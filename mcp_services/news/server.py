from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

# Initialize FastMCP server
mcp = FastMCP("News Service")

@mcp.tool()
def search_global_news(query: str = "global major news") -> str:
    """
    Searches for global major news from the last 24 hours using DuckDuckGo.
    
    Args:
        query: The search query (default: "global major news").
        
    Returns:
        A string containing a list of news items with titles, bodies, and URLs.
    """
    results = []
    try:
        # keywords: search query
        # region: wt-wt (World)
        # safesearch: on
        # timelimit: d (day - last 24 hours)
        # max_results: 10
        with DDGS() as ddgs:
            ddgs_news = ddgs.news(
                keywords=query,
                region="wt-wt",
                safesearch="on",
                timelimit="d",
                max_results=10
            )
            for r in ddgs_news:
                results.append(f"Title: {r.get('title')}\nSource: {r.get('source')}\nDate: {r.get('date')}\nLink: {r.get('url')}\nSummary: {r.get('body')}\n")
    except Exception as e:
        return f"Error searching news: {str(e)}"

    if not results:
        return "No news found for the given query in the last 24 hours."

    return "\n---\n".join(results)

if __name__ == "__main__":
    # Run via stdio by default when executed
    mcp.run(transport='stdio')
