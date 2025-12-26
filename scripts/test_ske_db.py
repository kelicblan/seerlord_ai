import asyncio
import sys
import os

# Add project root to path so we can import server modules
sys.path.append(os.getcwd())

from server.ske.database import Neo4jManager
from server.ske.config import ske_settings
from loguru import logger

async def main():
    logger.info("Testing SKE Neo4j Connection and Index Creation...")
    logger.info(f"URL: {ske_settings.NEO4J_URI}")
    logger.info(f"User: {ske_settings.NEO4J_USERNAME}")
    logger.info(f"Database: {ske_settings.NEO4J_DATABASE}")
    
    try:
        # 1. Connect
        driver = await Neo4jManager.get_driver()
        logger.info("Driver obtained successfully.")
        
        # 2. Create Indexes
        await Neo4jManager.create_indexes()
        logger.info("Indexes creation command executed.")
        
        # 3. Verify Indexes
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            # Check for Vector Index
            # SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties
            result = await session.run("SHOW INDEXES")
            records = await result.data()
            
            index_names = [r["name"] for r in records]
            logger.info(f"Existing Indexes: {index_names}")
            
            found_vector = False
            for r in records:
                if r["name"] == "entity_embedding_index":
                    found_vector = True
                    logger.info(f"Found Vector Index: {r}")
                    break
            
            if found_vector:
                logger.info("✅ SUCCESS: Vector Index 'entity_embedding_index' verified.")
            else:
                logger.error("❌ FAILURE: Vector Index 'entity_embedding_index' NOT found.")

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
    finally:
        await Neo4jManager.close()

if __name__ == "__main__":
    asyncio.run(main())
