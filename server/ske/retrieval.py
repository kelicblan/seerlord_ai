import asyncio
from typing import List, Dict, Any, Set, Tuple
from loguru import logger
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from server.ske.database import Neo4jManager, ske_settings
import server.ske.llm_setup as llm_setup

class RetrievedNode(BaseModel):
    id: str
    text: str
    type: str # "Entity" or "Chunk"
    score: float
    metadata: Dict[str, Any] = {}

class GraphRAGRetriever:
    """
    Implements SOTA GraphRAG retrieval logic:
    1. Hybrid Retrieval (Vector + Graph)
    2. Parallel Execution
    3. Rerank & Generation
    """
    
    def __init__(self):
        if not llm_setup.ske_langchain_llm or not llm_setup.ske_langchain_embeddings:
            raise RuntimeError("SKE LLM/Embeddings not initialized. Call initialize_ske_llm() first.")
        self.llm = llm_setup.ske_langchain_llm
        self.embeddings = llm_setup.ske_langchain_embeddings

    async def _get_embedding(self, text: str) -> List[float]:
        return await self.embeddings.aembed_query(text)

    async def _vector_search_entities(self, driver, embedding: List[float], top_k: int) -> List[RetrievedNode]:
        """
        Path 1.1: Vector Search on Entities
        """
        query = """
        CALL db.index.vector.queryNodes('entity_embedding_index', $k, $embedding)
        YIELD node, score
        RETURN node.id as id, node.name as name, node.type as type, node.description as description, score
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, k=top_k, embedding=embedding)
            nodes = []
            async for record in result:
                nodes.append(RetrievedNode(
                    id=record["id"] or "", 
                    text=f"{record['name']} ({record['type']}): {record['description']}",
                    type="Entity",
                    score=record["score"],
                    metadata={"name": record["name"], "type": record["type"]}
                ))
            return nodes

    async def _vector_search_chunks(self, driver, embedding: List[float], top_k: int) -> List[RetrievedNode]:
        """
        Path 1.2: Vector Search on Chunks
        """
        query = """
        CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
        YIELD node, score
        RETURN node.id as id, node.text as text, score
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, k=top_k, embedding=embedding)
            nodes = []
            async for record in result:
                nodes.append(RetrievedNode(
                    id=record["id"] or "",
                    text=record["text"],
                    type="Chunk",
                    score=record["score"]
                ))
            return nodes

    async def _graph_traversal(self, driver, seed_ids: List[str]) -> List[str]:
        """
        Path 2: Graph Traversal (1-hop neighbors)
        """
        if not seed_ids:
            return []
            
        # Find neighbors for these nodes
        # If seed is Chunk: (Chunk)-[:MENTIONS]->(Entity)
        # If seed is Entity: (Entity)-[:RELATED_TO|GENERATED]-(Entity)
        query = """
        MATCH (n) WHERE elementId(n) IN $ids OR n.id IN $ids
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN m.name as name, m.text as text, m.description as description, type(r) as rel_type
        LIMIT 20
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, ids=seed_ids)
            
            context_parts = []
            async for record in result:
                name = record["name"]
                text = record["text"]
                desc = record["description"]
                rel = record["rel_type"]
                
                content = text or desc or name or ""
                if content:
                    context_parts.append(f"-- [{rel}] --> {content}")
            
            return context_parts

    async def search(self, query: str, top_k: int = 5) -> str:
        """
        Executes the full GraphRAG pipeline.
        """
        logger.info(f"GraphRAG Search: {query}")
        
        # 1. Generate Embedding
        embedding = await self._get_embedding(query)
        
        driver = await Neo4jManager.get_driver()
        
        # 2. Parallel Vector Search (Path 1)
        # We run Entity and Chunk search concurrently with separate sessions
        task_entities = self._vector_search_entities(driver, embedding, top_k)
        task_chunks = self._vector_search_chunks(driver, embedding, top_k)
        
        results = await asyncio.gather(task_entities, task_chunks)
        entity_nodes, chunk_nodes = results
        
        all_nodes = entity_nodes + chunk_nodes
        # Sort by score
        all_nodes.sort(key=lambda x: x.score, reverse=True)
        top_nodes = all_nodes[:top_k]
        
        # Collect IDs for graph traversal
        seed_ids = [n.id for n in top_nodes if n.id]
        
        # 3. Graph Traversal (Path 2)
        # Find 1-hop neighbors for the top retrieved nodes
        neighbor_texts = await self._graph_traversal(driver, seed_ids)
        
        # 4. Context Construction
        context_list = []
        context_list.append("--- Retrieved Entities/Chunks ---")
        for node in top_nodes:
            context_list.append(f"[{node.type}] {node.text}")
        
        context_list.append("\n--- Graph Context (Neighbors) ---")
        context_list.extend(neighbor_texts)
        
        full_context = "\n".join(context_list)
        
        # 5. Rerank & Generation (LLM)
        # In a full system, we might use a Cross-Encoder for Rerank.
        # Here we trust the Vector Score + Graph Context and let LLM synthesize.
        
        logger.info(f"Generating answer with context length: {len(full_context)}")
        
        prompt = ChatPromptTemplate.from_template(
            """You are an intelligent assistant powered by a Knowledge Graph.
Use the following context to answer the user's question. 
If the answer is not in the context, say so.

Context:
{context}

Question: {question}

Answer:"""
        )
        
        chain = prompt | self.llm | StrOutputParser()
        
        answer = await chain.ainvoke({
            "context": full_context,
            "question": query
        })
        
        return answer

