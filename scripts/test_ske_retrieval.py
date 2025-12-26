import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from server.ske.llm_setup import initialize_ske_llm
from server.ske.retrieval import GraphRAGRetriever
from server.ske.database import Neo4jManager

async def test_retrieval():
    print("Initializing LLM...")
    initialize_ske_llm()
    
    retriever = GraphRAGRetriever()
    
    query = "SEERLORD 的动态记忆机制是什么？"
    print(f"\nTesting GraphRAG Search for: '{query}'\n")
    
    answer = await retriever.search(query)
    
    print("\n" + "="*50)
    print("FINAL ANSWER:")
    print("="*50)
    print(answer)
    print("="*50)
    
    await Neo4jManager.close()

if __name__ == "__main__":
    asyncio.run(test_retrieval())
