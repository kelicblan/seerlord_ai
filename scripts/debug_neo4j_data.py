import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from server.ske.database import Neo4jManager, ske_settings

async def debug_data():
    driver = await Neo4jManager.get_driver()
    async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
        # Get a chunk
        result = await session.run("MATCH (c:Chunk) RETURN c.id as id, c.text as text LIMIT 1")
        record = await result.single()
        if not record:
            logger.warning("No chunks found.")
            return
        
        chunk_id = record["id"]
        logger.info(f"Checking Chunk ID: {chunk_id}")
        logger.info(f"Text: {record['text'][:50]}...")
        
        # Check mentions
        mentions = await session.run(
            "MATCH (c:Chunk {id: $id})-[:MENTIONS]->(e:Entity) RETURN e.name, e.type",
            id=chunk_id
        )
        found = False
        async for r in mentions:
            found = True
            logger.info(f"  -> Mentions: {r['e.name']} ({r['e.type']})")
        
        if not found:
            logger.warning("  No MENTIONS relationships found for this chunk.")

if __name__ == "__main__":
    asyncio.run(debug_data())
