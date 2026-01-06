import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.plugins.news_reporter.graph import search_node, summarize_node, NewsState

async def test_empty_news_handling():
    print("🚀 Starting Empty News Handling Test...")
    
    # Simulate state with empty news content
    state: NewsState = {
        "messages": [],
        "tenant_id": "test",
        "user_id": "test",
        "memory_context": "",
        "skills_context": "",
        "news_content": "", # Empty content
        "latest_summary": ""
    }
    
    # 1. Test Search Node (Mocking failure is hard without mocking the tool, 
    # but we can test how summarize_node handles the result of a failed search)
    
    # Let's say search_node returned this (simulating the proposed fix):
    state["news_content"] = "Error: Fetched content is too short."
    
    print(f"📝 Mock Search Result: {state['news_content']}")
    
    # 2. Test Summarize Node
    print("\n🔍 Running Summarize Node...")
    result = await summarize_node(state)
    
    summary = result.get("latest_summary", "")
    print(f"✅ Summarize Output (Preview): {summary[:100]}...")
    
    if "⚠️" in summary:
        print("✅ Correctly identified error state.")
    else:
        print("❌ Failed to identify error state.")

if __name__ == "__main__":
    asyncio.run(test_empty_news_handling())
