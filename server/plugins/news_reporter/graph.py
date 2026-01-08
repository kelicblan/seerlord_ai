from typing import TypedDict, List, Annotated, Optional
import operator
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from server.core.llm import get_llm
from server.kernel.mcp_manager import mcp_manager
from server.kernel.registry import registry
# Memory node removed as per requirements
# from server.memory.tools import memory_node 
from loguru import logger
import uuid
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from server.kernel.skill_integration import skill_injector
from server.plugins.news_reporter.state import NewsState

# Node: Inject Agent Context
async def inject_agent_context(state: NewsState):
    """
    Injects the agent description into the state before skill loading.
    """
    from server.plugins.news_reporter.plugin import plugin
    return {"agent_description": plugin.description}

# Node: Search News
async def search_node(state: NewsState):
    """
    Searches for news using Bing Search via MCP with intent understanding.
    """
    messages = state.get("messages", [])
    user_input = ""
    if messages and isinstance(messages[-1], HumanMessage):
        user_input = messages[-1].content.strip()

    # 1. Intent Extraction / Query Generation
    query = "latest global news"
    if user_input:
        try:
            llm = get_llm(temperature=0)
            query_prompt = (
                "You are a search query generator. "
                "Convert the user's request into a specific, effective search query for a news search engine.\n"
                "Focus on finding specific news articles.\n"
                "If the user asks for 'latest news' without specific topic, return 'latest global news'.\n"
                "Return ONLY the query string, no quotes or explanation.\n\n"
                f"User Request: {user_input}"
            )
            response = await llm.ainvoke([SystemMessage(content=query_prompt)])
            query = response.content.strip()
            logger.info(f"Generated search query: '{query}' from user input: '{user_input}'")
        except Exception as e:
            logger.warning(f"Failed to generate query with LLM, using raw input. Error: {e}")
            query = user_input

    # 2. Use the 'bing_search' MCP tool
    tool = mcp_manager.get_tool("bingcn", "bing_search")
    
    if not tool:
        logger.warning("MCP Tool 'bing_search' (server: bingcn) not found.")
        return {"news_content": "Error: Bing Search tool is unavailable."}

    # 3. Call the tool
    try:
        logger.info(f"Searching news with query: {query}")
        
        # Invoke tool with query and count=20
        # Assuming the underlying MCP tool handles extra parameters or specifically supports 'count'
        search_results = await tool.ainvoke({"query": query, "count": 20})
        
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
        return {"news_content": f"Error searching news: {str(e)}", "search_query": query}
    
    return {"news_content": news_content, "search_query": query}

# Node: Summarize News
async def summarize_node(state: NewsState):
    """
    Summarizes the news content into a list using LLM.
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
    search_query = state.get("search_query", "Latest News")

    # Updated Prompt for List Generation
    base_prompt = (
        f"You are a professional News Assistant providing a report on: '{search_query}'.\n"
        "Your task is to analyze the search results and generate a clean, organized news list based on the search results.\n"
        "The user wants a comprehensive list of news items (aim for 20 items if data permits).\n\n"
        f"[Expert Guidelines]:\n{skills}\n\n"
        "Requirements:\n"
        "1. Extract key news items from the search results.\n"
        "2. Translate titles/summaries to Simplified Chinese.\n"
        "3. Format each item strictly as a Markdown list item:\n"
        "   - `[Title in Chinese](link) (Source) - Time`\n"
        "   - If 'Time' is not available, omit it.\n"
        "   - If 'Source' is not available, try to infer from the domain.\n"
        "4. DO NOT add summary text under items unless necessary for context.\n"
        "5. Group them under a header like '## � Latest News / 最新新闻'.\n"
        "6. If there are many results, prioritize the most recent and relevant ones.\n"
        "7. Maintain a professional, objective tone.\n"
        f"Search Results:\n{news_content[:50000]}" # Increased limit to handle more results
    )

    try:
        llm = get_llm(temperature=0.5)
        response = await llm.ainvoke([SystemMessage(content=base_prompt)])
    except Exception as e:
        logger.error(f"Error invoking LLM: {e}")
        msg = f"⚠️ **生成简报失败**\n\n原因：LLM 调用出错 - {str(e)}"
        return {"latest_summary": msg, "messages": [AIMessage(content=msg)]}
    
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
                        title="新闻简报",
                        description="自动生成的新闻摘要内容",
                    ))
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to save content artifact: {e}")
    return {}

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
        prompt = (
            "Please send this news summary via email.\n"
            "Target Agent ID: news_reporter\n"
            "Subject: SeerLord AI: 最新新闻简报\n"
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

graph_builder.add_node("inject_context", inject_agent_context)
graph_builder.add_node("load_skills", skill_injector.load_skills_context)
graph_builder.add_node("search_news", search_node)
graph_builder.add_node("summarize_news", summarize_node)
graph_builder.add_node("email_news", email_node)
graph_builder.add_node("finalize_news", finalize_node)

graph_builder.add_edge(START, "inject_context")
graph_builder.add_edge("inject_context", "load_skills")
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
