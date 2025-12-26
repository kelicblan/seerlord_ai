import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from server.ske.ingestion import process_document
from server.ske.database import Neo4jManager, ske_settings
from loguru import logger

async def main():
    test_file = os.path.join("Temp_Files", "test_ske.txt")
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        return

    logger.info("Starting Ingestion Test...")
    try:
        # Run Ingestion
        await process_document(test_file)
        
        # Verify in Neo4j
        driver = await Neo4jManager.get_driver()
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            logger.info("Verifying Data in Neo4j...")
            
            # Check Document
            result = await session.run("MATCH (d:Document {filename: 'test_ske.txt'}) RETURN d")
            doc = await result.single()
            if doc:
                logger.info("✅ Document node found.")
            else:
                logger.error("❌ Document node NOT found.")

            # Check Chunks
            result = await session.run("MATCH (d:Document {filename: 'test_ske.txt'})<-[:PART_OF]-(c:Chunk) RETURN count(c) as count")
            record = await result.single()
            count = record["count"]
            logger.info(f"✅ Found {count} Chunks.")
            
            # Check Entities
            result = await session.run("MATCH (c:Chunk)-[:MENTIONS]->(e:Entity) RETURN count(distinct e) as count")
            record = await result.single()
            e_count = record["count"]
            logger.info(f"✅ Found {e_count} Entities linked to Chunks.")
            
            # Check Relationships
            result = await session.run("MATCH (s:Entity)-[r:RELATED_TO]->(o:Entity) RETURN s.name, r.type, o.name LIMIT 5")
            records = await result.data()
            if records:
                logger.info("✅ Found relationships:")
                for r in records:
                    logger.info(f"   ({r['s.name']}) -[{r['r.type']}]-> ({r['o.name']})")
            else:
                logger.warning("⚠️ No relationships found (extraction might have failed or found none).")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        await Neo4jManager.close()

if __name__ == "__main__":
    asyncio.run(main())
