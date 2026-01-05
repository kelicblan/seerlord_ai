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
    Fetches tech news from NewsMinimalist using web-tools (Headless mode).
    """
    # Use the new 'web-tools' MCP tool - PREFER HEADLESS for JS sites
    tool = mcp_manager.get_tool("web-tools", "fetch_headless_content")
    
    if not tool:
        # Fallback to standard fetch if headless not available
        logger.warning("MCP Tool 'fetch_headless_content' not found, falling back to 'fetch_url_content'")
        tool = mcp_manager.get_tool("web-tools", "fetch_url_content")

    if not tool:
        logger.error("No fetch tools found in 'web-tools'.")
        return {"news_content": "Error: Web fetch tool is unavailable."}

    # Call the tool
    try:
        # Note: from=2&to=10 captures more items (lower significance threshold) to meet the target of ~50 items.
        # To ensure we get enough items, we use headless browser with scrolling (implemented in web-tools).
        url = "https://www.newsminimalist.com/?category=all&from=2&to=10&sort=latest"
        logger.info(f"Fetching news from {url}...")
        
        # Pass wait_for_selector if using headless to ensure news items load
        # .news-item or similar common classes, but generic wait is safer if unknown
        news_content = await tool.ainvoke({"url": url})
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {"news_content": f"Error fetching news: {str(e)}"}
    
    return {"news_content": news_content}

# Node: Summarize News
async def summarize_node(state: NewsState):
    """
    Summarizes the news content using LLM.
    """
    news_content = state.get("news_content", "")
    
    if not news_content or "Error fetching" in news_content:
        logger.warning(f"News content is empty or error: {news_content[:100]}")
        msg = "⚠️ **无法获取最新的科技新闻数据**\n\n数据源暂时无法访问（可能由于网络波动或访问频率限制）。请稍后再试。\n\n"
        if "429" in news_content:
            msg += "*(错误代码: 429 Too Many Requests)*"
        return {"latest_summary": msg, "messages": [AIMessage(content=msg)]}

    skills = state.get("skills_context", "")

    base_prompt = (
        "You are a 'Private Intelligence Officer' for SeerLord AI.\n"
        "Your task is to parse the raw text from NewsMinimalist and generate a clean, Chinese briefing.\n"
        "Raw content usually contains news items with titles, scores, and sources.\n\n"
        f"[Expert Guidelines]:\n{skills}\n\n"
        "Requirements:\n"
        "1. Extract AT LEAST 50 technology news items. Do not stop at 10. If there are fewer than 50, extract all of them.\n"
        "2. Translate titles to Simplified Chinese.\n"
        "3. Format each item strictly as: `[Chinese Title](original_link) (Source) - Time`.\n"
        "   - If 'Time' is not available, omit it or use 'Recently'.\n"
        "   - If 'Source' is not available, omit it.\n"
        "4. DO NOT add summary text under items.\n"
        "5. Group them under a header like '## 🚀 Tech Intelligence'.\n"
        "6. Maintain a professional, objective tone.\n"
        f"Raw News Data:\n{news_content[:80000]}" # Increased limit to capture ~50 items
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
graph_builder.add_edge("summarize_news", "email_news")
graph_builder.add_edge("email_news", "finalize_news")
graph_builder.add_edge("finalize_news", END)

# Compile Graph
app = graph_builder.compile()
