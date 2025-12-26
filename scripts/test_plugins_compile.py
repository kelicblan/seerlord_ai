import sys
import os
import asyncio

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_compile():
    plugins = [
        "server.plugins.requirement_analyst.graph",
        "server.plugins.ppt_generator.graph",
        "server.plugins.tutorial_generator.graph",
        "server.plugins._voyager_agent_.graph",
        "server.plugins._skill_evolver_.graph",
        "server.plugins.news_reporter.graph",
        "server.plugins.fta_agent.graph",
        "server.plugins._example_agent.graph",
    ]

    for plugin_module in plugins:
        try:
            print(f"Testing compilation of {plugin_module}...")
            # Dynamic import
            module = __import__(plugin_module, fromlist=['app'])
            if hasattr(module, 'app'):
                print(f"✅ {plugin_module} compiled successfully.")
            else:
                print(f"⚠️ {plugin_module} imported but 'app' object not found.")
        except Exception as e:
            print(f"❌ {plugin_module} failed to compile/import: {e}")

if __name__ == "__main__":
    asyncio.run(test_compile())
