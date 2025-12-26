import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.ske.agent.workflow import ske_agent
from loguru import logger

async def main():
    logger.info("Starting SKE Agent Test...")
    
    question = "SeerLord AI 支持哪些编程语言？"
    
    logger.info(f"Question: {question}")
    
    initial_state = {
        "question": question,
        "context": [],
        "answer": None,
        "search_results": []
    }
    
    try:
        # Run the graph
        result = await ske_agent.ainvoke(initial_state)
        
        print("\n" + "="*50)
        print(f"🤖 Question: {question}")
        print("-" * 20)
        print(f"📚 Retrieved Context ({len(result['search_results'])} items):")
        for item in result['search_results']:
            print(f" - [{item['type']}] {item['content'][:100]}...")
        print("-" * 20)
        print(f"💡 Answer:\n{result['answer']}")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
