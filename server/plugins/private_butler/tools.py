from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from loguru import logger
from server.ske.retrieval import GraphRAGRetriever
from server.ske.ingestion import extract_triplets, get_embedding
from server.ske.database import Neo4jManager, ske_settings
from server.ske.models import RelationshipType
from pydantic import BaseModel, Field
import uuid

# --- Tool Schemas ---

class MemoryWriteInput(BaseModel):
    fact: str = Field(..., description="The fact or information to store in memory (e.g., 'Sarah likes lilies').")

class MemorySearchInput(BaseModel):
    query: str = Field(..., description="The question to ask the memory (e.g., 'What does Sarah like?').")

# --- Tool Implementations ---

from langchain_core.runnables import RunnableConfig

@tool("memory_write", args_schema=MemoryWriteInput)
async def memory_write(fact: str, config: RunnableConfig) -> str:
    """
    Stores a new fact or piece of information into the Personal Knowledge Graph.
    Use this when the user shares personal details, preferences, or event information.
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "Error: No user_id provided in context."
        
    logger.info(f"Writing to memory for user {user_id}: {fact}")
    
    try:
        # 1. Extract Triplets
        triplets = await extract_triplets(fact)
        if not triplets:
            return "Could not extract structured information from the input."
            
        driver = await Neo4jManager.get_driver()
        
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            count = 0
            for triplet in triplets:
                # 2. Embedding
                subj_embedding = await get_embedding(triplet.subject)
                obj_embedding = await get_embedding(triplet.object)
                
                # 3. Write to Neo4j
                # Merge Subject
                await session.run(
                    """
                    MERGE (e:Entity {name: $name, type: $type, user_id: $user_id})
                    ON CREATE SET 
                        e.id = randomUUID(),
                        e.embedding = $embedding,
                        e.description = $name + ' (' + $type + ')'
                    ON MATCH SET
                        e.embedding = $embedding 
                    """,
                    name=triplet.subject,
                    type=triplet.subject_type,
                    user_id=user_id,
                    embedding=subj_embedding
                )
                
                # Merge Object
                await session.run(
                    """
                    MERGE (e:Entity {name: $name, type: $type, user_id: $user_id})
                    ON CREATE SET 
                        e.id = randomUUID(),
                        e.embedding = $embedding,
                        e.description = $name + ' (' + $type + ')'
                    ON MATCH SET
                        e.embedding = $embedding
                    """,
                    name=triplet.object,
                    type=triplet.object_type,
                    user_id=user_id,
                    embedding=obj_embedding
                )
                
                # Merge Relationship
                await session.run(
                    """
                    MATCH (s:Entity {name: $s_name, type: $s_type, user_id: $user_id})
                    MATCH (o:Entity {name: $o_name, type: $o_type, user_id: $user_id})
                    MERGE (s)-[r:RELATED_TO {type: $predicate}]->(o)
                    """,
                    s_name=triplet.subject,
                    s_type=triplet.subject_type,
                    o_name=triplet.object,
                    o_type=triplet.object_type,
                    user_id=user_id,
                    predicate=triplet.predicate
                )
                count += 1
                
        return f"Successfully stored {count} facts in memory for user {user_id}."
        
    except Exception as e:
        logger.error(f"Memory write failed: {e}")
        return f"Error writing to memory: {e}"

@tool("memory_read", args_schema=MemorySearchInput)
async def memory_read(query: str, config: RunnableConfig) -> str:
    """
    Retrieves information from the Personal Knowledge Graph.
    Use this to answer questions about the user's life, history, or preferences.
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "Error: No user_id provided in context."

    try:
        retriever = GraphRAGRetriever()
        answer = await retriever.search(query, user_id=user_id)
        return answer
    except Exception as e:
        logger.error(f"Memory read failed: {e}")
        return f"Error reading memory: {e}"
