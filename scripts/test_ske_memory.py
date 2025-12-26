import asyncio
import uuid
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from server.ske.llm_setup import initialize_ske_llm
from server.ske.memory_manager import MemoryManager
from server.ske.database import Neo4jManager

async def test_memory():
    print("Initializing LLM...")
    initialize_ske_llm()
    
    session_id = str(uuid.uuid4())
    content = """
    经过分析，我认为 SEERLORD 系统的核心优势在于其动态记忆机制（Dynamic Memory）。
    这种机制允许 Agent 将运行时的洞察（Insight）实时沉淀到知识图谱中。
    相比于传统的 RAG，这是一种主动学习（Active Learning）的体现。
    """
    
    print(f"Testing save_agent_insight with session_id: {session_id}")
    await MemoryManager.save_agent_insight(session_id, content)
    
    # Verify
    print("Verifying in Neo4j...")
    driver = await Neo4jManager.get_driver()
    async with driver.session() as session:
        result = await session.run("""
            MATCH (s:AgentSession {session_id: $sid})-[r:GENERATED]->(e:Entity)
            RETURN s, r, e
        """, sid=session_id)
        
        records = [record async for record in result]
        print(f"Found {len(records)} generated entities linked to session.")
        for record in records:
            e = record["e"]
            print(f" - Entity: {e.get('name')} ({e.get('type')})")
            print(f"   Reasoning: {record['r'].get('reasoning')}")
            
    await Neo4jManager.close()

if __name__ == "__main__":
    asyncio.run(test_memory())
