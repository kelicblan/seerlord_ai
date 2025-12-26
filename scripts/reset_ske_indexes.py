import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from server.ske.database import Neo4jManager, ske_settings

async def reset_indexes():
    logger.info("Resetting SKE Indexes...")
    driver = await Neo4jManager.get_driver()
    
    async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
        # Drop existing vector indexes
        logger.info("Dropping existing vector indexes...")
        try:
            await session.run("DROP INDEX entity_embedding_index IF EXISTS")
            logger.info("Dropped entity_embedding_index")
        except Exception as e:
            logger.warning(f"Failed to drop entity_embedding_index: {e}")

        try:
            await session.run("DROP INDEX chunk_embedding_index IF EXISTS")
            logger.info("Dropped chunk_embedding_index")
        except Exception as e:
            logger.warning(f"Failed to drop chunk_embedding_index: {e}")

    await Neo4jManager.close()
    
    # Re-create indexes using Neo4jManager logic (which uses new config)
    await Neo4jManager.create_indexes()
    logger.info("Indexes reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_indexes())
