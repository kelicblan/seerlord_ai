from typing import TypedDict, List, Annotated, Optional
import operator
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from server.core.llm import get_llm
from server.kernel.mcp_manager import mcp_manager
from loguru import logger

# Define State
class NewsState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    news_content: str
    critique_count: int
    latest_summary: str

# Define Structured Output for Critique
class CritiqueResult(BaseModel):
    score: int = Field(description="Score from 1 to 10. 10 is perfect.")
    critique: str = Field(description="Detailed critique of the summary.")
    suggestions: str = Field(description="Specific suggestions for improvement.")

# Node: Search News
async def search_node(state: NewsState):
    """
    Searches for global news using the MCP tool.
    """
    # Try to get the tool from MCP Manager
    # Prefer 'bingcn' (User requested), fallback to 'news_service'
    tool = mcp_manager.get_tool("bingcn", "bing_search")
    
    if not tool:
        logger.warning("MCP Tool 'bing_search' not found in 'bingcn'. Falling back to 'news_service'.")
        tool = mcp_manager.get_tool("news_service", "search_global_news")
    
    if not tool:
        logger.error("No news search tool available.")
        return {"news_content": "Error: News search tool is unavailable (MCP connection failed or tool missing)."}

    # Call the tool
    try:
        # bing_search usually takes 'query' or 'keywords'. We use 'query' as a safe bet for now.
        # If it's the python news_service, it also takes 'query'.
        # We search for recent major news.
        news_results = await tool.ainvoke({"query": "24小时内全球重大新闻"})
    except Exception as e:
        logger.error(f"Error calling MCP tool: {e}")
        return {"news_content": f"Error searching news: {str(e)}"}
    
    return {"news_content": news_results, "critique_count": 0}

# Node: Summarize News
async def summarize_node(state: NewsState):
    """
    Summarizes the news content using LLM.
    """
    news_content = state.get("news_content", "")
    current_summary = state.get("latest_summary", "")
    
    # 提取反馈历史
    messages = state.get("messages", [])
    feedback_history = []
    for msg in reversed(messages):
        if hasattr(msg, 'content') and "[Critic Feedback]" in msg.content:
            feedback_history.append(msg.content)
            if len(feedback_history) >= 2: break
            
    feedback_context = ""
    if feedback_history:
        feedback_context = "\n\n[Previous Feedback to Address]:\n" + "\n".join(feedback_history)

    if not news_content:
        return {"messages": [AIMessage(content="Sorry, I couldn't find any major global news in the last 24 hours.")]}

    base_prompt = (
        "You are a professional news editor for 'SeerLord AI'.\n"
        "Your task is to summarize the provided global news articles into a concise, engaging Daily Briefing.\n"
        "Requirements:\n"
        "1. Use Markdown format.\n"
        "2. Group news by topic if possible.\n"
        "3. Use emojis for each section.\n"
        "4. Include the source and a link for each item if available.\n"
        "5. Keep it under 1000 words.\n"
        "6. Language: Chinese (Simplified).\n"
        f"{feedback_context}\n\n"
    )

    if current_summary:
        # We are revising (Local Loop or Global Loop)
        prompt = (
            f"{base_prompt}"
            f"Previous Summary:\n{current_summary}\n\n"
            "Please revise the summary based on the feedback."
        )
    else:
        # First draft
        prompt = (
            f"{base_prompt}"
            f"Raw News Data:\n{news_content}"
        )

    llm = get_llm(temperature=0.5)
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    return {"latest_summary": response.content, "messages": [response]}

# Node: Critique News
async def critique_node(state: NewsState):
    """
    Critiques the generated summary.
    """
    summary = state.get("latest_summary", "")
    if not summary:
        return {"critique_feedback": "No summary generated.", "score": 0}

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(CritiqueResult)

    prompt = (
        "You are a strict Senior Editor.\n"
        "Review the following News Briefing.\n"
        "Check for:\n"
        "1. Clarity and flow.\n"
        "2. Proper formatting (Markdown, emojis).\n"
        "3. Completeness (did it miss major points from raw data? - Hard to know without raw data, but check internal consistency).\n"
        "4. Professional tone.\n\n"
        f"Briefing:\n{summary}"
    )

    try:
        result = await structured_llm.ainvoke([SystemMessage(content=prompt)])
        score = result.score
        feedback = f"Score: {score}/10. Critique: {result.critique}. Suggestions: {result.suggestions}"
    except Exception as e:
        logger.error(f"Critique failed: {e}")
        score = 10 # Assume good if critique fails to avoid loops
        feedback = "Critique failed."

    return {
        "critique_feedback": feedback,
        "score": score,
        "critique_count": state.get("critique_count", 0) + 1
    }

# Conditional Logic
def should_revise(state: NewsState):
    """
    Decides whether to revise or finish.
    """
    score = state.get("score", 0)
    count = state.get("critique_count", 0)
    
    if score >= 8 or count >= 3:
        return "end"
    return "revise"

# Finalize Node (Optional, just to wrap up)
async def finalize_node(state: NewsState):
    return {"messages": [AIMessage(content=state["latest_summary"])]}

# Build Graph
graph_builder = StateGraph(NewsState)

graph_builder.add_node("search_news", search_node)
graph_builder.add_node("summarize_news", summarize_node)
graph_builder.add_node("critique_news", critique_node)
graph_builder.add_node("finalize_news", finalize_node)

graph_builder.add_edge(START, "search_news")
graph_builder.add_edge("search_news", "summarize_news")
graph_builder.add_edge("summarize_news", "critique_news")

graph_builder.add_conditional_edges(
    "critique_news",
    should_revise,
    {
        "revise": "summarize_news",
        "end": "finalize_news"
    }
)

graph_builder.add_edge("finalize_news", END)

# Compile Graph
graph = graph_builder.compile()
