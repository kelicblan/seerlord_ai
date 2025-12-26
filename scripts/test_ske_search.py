import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from server.ske.search import SkeSearchService

async def main():
    query = "SeerLord AI Python"
    logger.info(f"Starting Search Test with query: '{query}'")
    
    try:
        results = await SkeSearchService.search(query, top_k=3)
        
        logger.info(f"Found {len(results)} results.")
        
        if not results:
            logger.warning("⚠️ No results found. Ensure data is ingested and indexes are created.")
            return

        for i, r in enumerate(results):
            content_preview = r.content[:100].replace('\n', ' ')
            logger.info(f"Result {i+1}: [{r.score:.4f}] {r.type} - {content_preview}...")
            if r.related:
                logger.info(f"  Related ({len(r.related)}): {', '.join([rel['name'] for rel in r.related])}")
            else:
                logger.info("  No related items found.")

        # Verification
        has_entity = any(r.type == "Entity" for r in results)
        has_chunk = any(r.type == "Chunk" for r in results)
        
        if has_entity:
            logger.info("✅ Entity search working.")
        else:
            logger.warning("⚠️ No Entities found (expected if query matches entities).")
            
        if has_chunk:
            logger.info("✅ Chunk search working.")
        else:
            logger.warning("⚠️ No Chunks found.")
            
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
