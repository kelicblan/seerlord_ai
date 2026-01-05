import os
import uuid
import asyncio
from typing import List, Tuple
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field

# LlamaIndex Imports
from llama_index.core import SimpleDirectoryReader, Document, Settings, PromptTemplate
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.program import LLMTextCompletionProgram

# Local Imports
from server.ske.config import ske_settings
from server.ske.database import Neo4jManager
from server.ske.models import RelationshipType
from server.ske.llm_setup import initialize_ske_llm

# --- Setup LlamaIndex Settings ---
initialize_ske_llm()

# --- Extraction Models ---

class Triplet(BaseModel):
    """
    Represents a Subject-Predicate-Object triple extracted from text.
    """
    subject: str = Field(..., description="The subject entity name")
    subject_type: str = Field(..., description="The type of the subject entity")
    predicate: str = Field(..., description="The relationship type (verb or preposition)")
    object: str = Field(..., description="The object entity name")
    object_type: str = Field(..., description="The type of the object entity")

class KnowledgeExtraction(BaseModel):
    """
    Container for extracted triplets.
    """
    triplets: List[Triplet] = Field(default_factory=list, description="List of extracted triplets")

# --- Ingestion Logic ---

async def get_embedding(text: str) -> List[float]:
    """
    Wrapper to get embedding using the configured model.
    """
    return await Settings.embed_model.aget_text_embedding(text)

async def extract_triplets(text: str) -> List[Triplet]:
    """
    Extracts knowledge triplets from a text chunk using LLM.
    """
    prompt_template_str = """
    You are a knowledge graph expert. Your task is to extract structured knowledge from the given text.
    Extract entities and their relationships in the form of (Subject, Predicate, Object) triplets.
    
    Guidelines:
    1. Identify key entities (Subject, Object) and classify their types (e.g., Person, Organization, Concept, Location, etc.).
    2. Identify the relationship (Predicate) between them. Use precise verbs or relationship names (e.g., "FOUNDED", "LOCATED_IN", "PART_OF").
    3. Be concise but accurate.
    4. CRITICAL: If the text refers to the speaker or writer (e.g., "I", "me", "my", "我"), ALWAYS use "User" as the entity name.
    
    Text: {text}
    
    Output the result as a list of JSON objects matching the schema.
    """
    
    template = PromptTemplate(prompt_template_str)
    
    try:
        # Use LlamaIndex's structured prediction
        result = await Settings.llm.astructured_predict(
            KnowledgeExtraction,
            template,
            text=text
        )
        return result.triplets
    except Exception as e:
        logger.error(f"Failed to extract triplets: {e}")
        return []

async def process_document(file_path: str, user_id: str):
    """
    Main pipeline function:
    1. Read File
    2. Chunking
    3. Embedding (Chunk)
    4. Extraction (Entities & Relations)
    5. Embedding (Entities)
    6. Storage (Neo4j) with user_id
    """
    logger.info(f"Processing document: {file_path} for user {user_id}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Read File
    reader = SimpleDirectoryReader(input_files=[file_path])
    documents = reader.load_data()
    
    if not documents:
        logger.warning(f"No content read from {file_path}")
        return

    filename = os.path.basename(file_path)
    
    # 2. Chunking
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents(documents)
    
    logger.info(f"Generated {len(nodes)} chunks from {filename}")
    
    # Prepare Neo4j Driver
    driver = await Neo4jManager.get_driver()
    
    async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
        
        # 3. Create Document Node (Once)
        await session.run(
            """
            MERGE (d:Document {filename: $filename, user_id: $user_id})
            ON CREATE SET d.upload_date = datetime()
            """,
            filename=filename,
            user_id=user_id
        )

        for i, node in enumerate(nodes):
            chunk_text = node.get_content()
            chunk_index = i
            
            # 4. Embedding (Chunk)
            chunk_embedding = await get_embedding(chunk_text)
            
            # 5. Storage (Chunk)
            chunk_id_result = await session.run(
                """
                MATCH (d:Document {filename: $filename, user_id: $user_id})
                CREATE (c:Chunk {
                    text: $text,
                    index: $index,
                    embedding: $embedding,
                    user_id: $user_id,
                    id: randomUUID()
                })
                MERGE (c)-[:PART_OF]->(d)
                RETURN c.id as id
                """,
                filename=filename,
                user_id=user_id,
                text=chunk_text,
                index=chunk_index,
                embedding=chunk_embedding
            )
            chunk_record = await chunk_id_result.single()
            chunk_id = chunk_record["id"]
            
            # 6. Extraction (Triplets)
            triplets = await extract_triplets(chunk_text)
            logger.info(f"Chunk {i}: Extracted {len(triplets)} triplets")
            
            for triplet in triplets:
                # 7. Embedding (Entities)
                subj_embedding = await get_embedding(triplet.subject)
                obj_embedding = await get_embedding(triplet.object)
                
                # 8. Storage (Entities & Relationships)
                
                # Merge Subject Entity
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
                
                # Merge Object Entity
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
                
                # Create Relationship between Entities
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
                
                # 9. Traceability: (Chunk)-[:MENTIONS]->(Entity)
                await session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (s:Entity {name: $s_name, type: $s_type, user_id: $user_id})
                    MERGE (c)-[:MENTIONS]->(s)
                    """,
                    chunk_id=chunk_id,
                    s_name=triplet.subject,
                    s_type=triplet.subject_type,
                    user_id=user_id
                )
                
                await session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (o:Entity {name: $o_name, type: $o_type, user_id: $user_id})
                    MERGE (c)-[:MENTIONS]->(o)
                    """,
                    chunk_id=chunk_id,
                    o_name=triplet.object,
                    o_type=triplet.object_type,
                    user_id=user_id
                )

    logger.info(f"Finished processing {filename}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        asyncio.run(process_document(sys.argv[1], sys.argv[2]))
    else:
        print("Usage: python ingestion.py <file_path> <user_id>")
