import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from llama_index.core import Settings
from pydantic import BaseModel

from server.ske.database import Neo4jManager, ske_settings
from server.ske.llm_setup import initialize_ske_llm

# Ensure LLM/Embeddings are initialized
initialize_ske_llm()

class SearchResultItem(BaseModel):
    """
    Unified search result item (Entity or Chunk).
    """
    id: str
    content: str
    type: str  # "Entity" or "Chunk"
    score: float
    metadata: Dict[str, Any] = {}
    related: List[Dict[str, Any]] = [] # Simple related items info

class SkeSearchService:
    
    @staticmethod
    async def get_query_embedding(query: str) -> List[float]:
        return await Settings.embed_model.aget_query_embedding(query)

    @classmethod
    async def search(cls, query: str, top_k: int = 5) -> List[SearchResultItem]:
        """
        Performs a hybrid search:
        1. Vector Search on Entities
        2. Vector Search on Chunks
        3. Graph Traversal for context (neighbors)
        """
        logger.info(f"Searching for: {query}")
        try:
            embedding = await cls.get_query_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise e

        driver = await Neo4jManager.get_driver()
        results: List[SearchResultItem] = []
        
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            
            # --- 1. Entity Search ---
            entity_query = """
            CALL db.index.vector.queryNodes('entity_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id as id, node.name as name, node.type as type, node.description as description, score
            """
            
            try:
                entity_records = await session.run(entity_query, k=top_k, embedding=embedding)
                
                async for record in entity_records:
                    # Get graph neighbors: (Entity)-[r]-(neighbor)
                    # We look for direct relationships to other Entities
                    neighbors_query = """
                    MATCH (e:Entity {id: $id})-[r]-(n:Entity)
                    RETURN type(r) as rel_type, n.name as name, n.type as type
                    LIMIT 5
                    """
                    neighbors_result = await session.run(neighbors_query, id=record["id"])
                    
                    related = []
                    async for r in neighbors_result:
                        related.append({
                            "rel": r["rel_type"], 
                            "name": r["name"], 
                            "type": r["type"]
                        })
                    
                    results.append(SearchResultItem(
                        id=record["id"],
                        content=record["name"],
                        type="Entity",
                        score=record["score"],
                        metadata={
                            "type": record["type"], 
                            "description": record.get("description")
                        },
                        related=related
                    ))
            except Exception as e:
                logger.error(f"Entity search failed: {e}")

            # --- 2. Chunk Search ---
            chunk_query = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id as id, node.text as text, score
            """
            
            try:
                chunk_records = await session.run(chunk_query, k=top_k, embedding=embedding)
                
                async for record in chunk_records:
                    # Get mentions: (Chunk)-[:MENTIONS]->(Entity)
                    mentions_query = """
                    MATCH (c:Chunk {id: $id})-[:MENTIONS]->(e:Entity)
                    RETURN e.name as name, e.type as type
                    LIMIT 5
                    """
                    mentions_result = await session.run(mentions_query, id=record["id"])
                    
                    related = []
                    async for r in mentions_result:
                        related.append({
                            "rel": "MENTIONS", 
                            "name": r["name"], 
                            "type": r["type"]
                        })

                    results.append(SearchResultItem(
                        id=record["id"],
                        content=record["text"],
                        type="Chunk",
                        score=record["score"],
                        metadata={},
                        related=related
                    ))
            except Exception as e:
                logger.error(f"Chunk search failed: {e}")

        # Sort combined results by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Return top_k * 2 (or just top_k? usually a mix is good, let's return more and let client filter)
        return results[:top_k * 2]

if __name__ == "__main__":
    # Simple CLI test
    import sys
    if len(sys.argv) > 1:
        async def main():
            results = await SkeSearchService.search(sys.argv[1])
            for r in results:
                print(f"[{r.score:.4f}] {r.type}: {r.content[:50]}...")
                for rel in r.related:
                    print(f"  -> {rel['rel']} {rel['name']}")
        
        asyncio.run(main())
    else:
        print("Usage: python search.py <query>")
