from langchain_core.tools import tool
from server.kernel.mcp_manager import mcp_manager
from loguru import logger

# 1. Local Tool Definition
@tool
def calculate_metrics(data: str) -> str:
    """
    Analyzes numerical data and returns metrics.
    Useful for calculating growth rates or sums from the research text.
    """
    # Dummy implementation
    return f"Calculated metrics for: {data[:20]}... [Mock Result]"

# 2. MCP Tool Wrapper (Helper)
async def search_web(query: str) -> str:
    """
    Wraps MCP search tool.
    """
    # Try to get a search tool (e.g., from 'bingcn' or 'brave')
    tool = mcp_manager.get_tool("bingcn", "bing_search")
    
    if not tool:
        # Fallback to a mock response if no MCP tool is available
        logger.warning("MCP Search tool not found. Using mock response.")
        return f"[Mock Search Result] Found information about: {query}. The market is growing."
        
    try:
        # MCP tools are Runnables
        result = await tool.ainvoke({"query": query})
        return str(result)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Error searching for {query}: {e}"
