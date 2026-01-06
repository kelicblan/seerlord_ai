from typing import TypedDict, List, Annotated, Optional
import operator
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from server.core.llm import get_llm
from server.kernel.mcp_manager import mcp_manager
from server.kernel.registry import registry
from server.memory.tools import memory_node
from loguru import logger
import uuid
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from server.kernel.skill_integration import skill_injector

# Define State
class NewsState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    # Context
    tenant_id: str
    user_id: str
    memory_context: str
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
    
    news_content: str
    latest_summary: str

# Node: Search News
async def search_node(state: NewsState):
    """
    Searches for tech news using Bing Search via MCP.
    """
    # Determine query from user input or default
    query = "latest technology news"
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], HumanMessage):
        user_input = messages[-1].content.strip()
        if user_input:
            query = user_input

    # Use the 'bing_search' MCP tool
    # Adjust server name 'bingcn' if necessary based on environment, or just search by tool name
    tool = mcp_manager.get_tool("bingcn", "bing_search")
    
    if not tool:
        # Fallback logic or error
        logger.warning("MCP Tool 'bing_search' (server: bingcn) not found.")
        # Try finding by tool name only if server name might differ
        # (This depends on mcp_manager implementation, usually get_tool requires server_name)
        return {"news_content": "Error: Bing Search tool is unavailable."}

    # Call the tool
    try:
        logger.info(f"Searching news with query: {query}")
        
        # Invoke tool with query
        search_results = await tool.ainvoke({"query": query})
        
        # Validation
        if not search_results:
             return {"news_content": "Error: No search results found."}
             
        # Convert to string if it's a list/dict
        if not isinstance(search_results, str):
            import json
            try:
                news_content = json.dumps(search_results, ensure_ascii=False, indent=2)
            except:
                news_content = str(search_results)
        else:
            news_content = search_results
            
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        return {"news_content": f"Error searching news: {str(e)}"}
    
    return {"news_content": news_content}

# Node: Summarize News
async def summarize_node(state: NewsState):
    """
    Summarizes the news content using LLM.
    """
    news_content = state.get("news_content", "")
    
    # Check for various error conditions
    is_error = (
        not news_content 
        or len(news_content) < 50 
        or "Error" in news_content[:50]
    )
    
    if is_error:
        logger.warning(f"News content is empty or error: {news_content[:100]}")
        msg = f"⚠️ **无法获取最新的新闻数据**\n\n原因：{news_content}\n\n"
        return {"latest_summary": msg, "messages": [AIMessage(content=msg)]}

    skills = state.get("skills_context", "")

    base_prompt = (
        "You are a 'Private Intelligence Officer' for SeerLord AI.\n"
        "Your task is to analyze the search results and generate a clean, Chinese briefing.\n\n"
        f"[Expert Guidelines]:\n{skills}\n\n"
        "Requirements:\n"
        "1. Extract key news items from the search results.\n"
        "2. Translate titles/summaries to Simplified Chinese.\n"
        "3. Format each item strictly as: `[Chinese Title](link) (Source) - Time`.\n"
        "   - Use the provided snippet/link in the search results.\n"
        "   - If 'Time' is not available, omit it.\n"
        "   - If 'Source' is not available, try to infer from the domain.\n"
        "4. DO NOT add summary text under items unless necessary for context.\n"
        "5. Group them under a header like '## 🚀 News Intelligence'.\n"
        "6. Maintain a professional, objective tone.\n"
        f"Search Results:\n{news_content[:20000]}"
    )

    llm = get_llm(temperature=0.5)
    response = await llm.ainvoke([SystemMessage(content=base_prompt)])
    
    return {"latest_summary": response.content, "messages": [response]}

# Finalize Node (Optional, just to wrap up)
async def finalize_node(state: NewsState):
    summary = state.get("latest_summary") or ""
    if summary:
        try:
            tenant_id = state.get("tenant_id")
            user_id = state.get("user_id")
            if tenant_id:
                async with SessionLocal() as db:
                    db.add(AgentArtifact(
                        id=str(uuid.uuid4()),
                        tenant_id=str(tenant_id),
                        user_id=str(user_id) if user_id else None,
                        agent_id="news_reporter",
                        type="content",
                        value=str(summary),
                        title="24小时全球重大新闻简报",
                        description="自动生成的新闻摘要内容",
                    ))
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to save content artifact: {e}")
    return {"messages": [AIMessage(content=summary)]}

# Node: Email News
async def email_node(state: NewsState, config: RunnableConfig):
    """
    Sends the generated summary via email using _mail_service_ system agent.
    """
    summary = state.get("latest_summary") or ""
    if not summary:
        logger.warning("No summary to email.")
        return {}

    logger.info("Calling _mail_service_ to send email...")

    # Get the mail service plugin
    mail_plugin = registry.get_plugin("_mail_service_")
    if not mail_plugin:
        logger.error("System Agent '_mail_service_' not found.")
        return {}

    try:
        # Call the mail agent graph
        mail_app = mail_plugin.get_graph()
        
        # Construct request for the mail agent
        # We explicitly state the target agent ID is 'news_reporter' so it looks up the config
        prompt = (
            "Please send this news summary via email.\n"
            "Target Agent ID: news_reporter\n"
            "Subject: SeerLord AI: 24小时全球重大新闻简报\n"
            f"Body:\n{summary}"
        )
        
        await mail_app.ainvoke({"messages": [HumanMessage(content=prompt)]})
        logger.info("Email request sent to _mail_service_.")
        
    except Exception as e:
        logger.error(f"Failed to invoke mail service: {e}")
        
    return {}

def should_email(state: NewsState):
    """Determine if we should send an email based on the summary content."""
    summary = state.get("latest_summary", "")
    # Don't email if it's an error message
    if "⚠️" in summary or "无法获取" in summary:
        return "finalize_news"
    return "email_news"

# Build Graph
graph_builder = StateGraph(NewsState)

graph_builder.add_node("load_skills", skill_injector.load_skills_context)
graph_builder.add_node("search_news", search_node)
graph_builder.add_node("summarize_news", summarize_node)
graph_builder.add_node("email_news", email_node)
graph_builder.add_node("finalize_news", finalize_node)

graph_builder.add_edge(START, "load_skills")
graph_builder.add_edge("load_skills", "search_news")
graph_builder.add_edge("search_news", "summarize_news")

# Conditional routing for email
graph_builder.add_conditional_edges(
    "summarize_news",
    should_email,
    {
        "email_news": "email_news",
        "finalize_news": "finalize_news"
    }
)

graph_builder.add_edge("email_news", "finalize_news")
graph_builder.add_edge("finalize_news", END)

# Compile Graph
app = graph_builder.compile()
