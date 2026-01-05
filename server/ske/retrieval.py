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

    async def _vector_search_entities(self, driver, embedding: List[float], user_id: str, top_k: int) -> List[RetrievedNode]:
        """
        Path 1.1: Vector Search on Entities (Filtered by User ID)
        """
        query = """
        CALL db.index.vector.queryNodes('entity_embedding_index', $k, $embedding)
        YIELD node, score
        WHERE node.user_id = $user_id
        RETURN node.id as id, node.name as name, node.type as type, node.description as description, score
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, k=top_k * 2, embedding=embedding, user_id=user_id) # Fetch more to filter
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

    async def _vector_search_chunks(self, driver, embedding: List[float], user_id: str, top_k: int) -> List[RetrievedNode]:
        """
        Path 1.2: Vector Search on Chunks (Filtered by User ID indirectly or TODO)
        Note: Chunks are linked to Documents. Documents should have user_id. 
        For now, let's assume Chunks might not have user_id directly on them unless we added it.
        Let's assume we update ingestion to add user_id to Chunks too, or filter by relation.
        For performance, filtering by property on the node is best.
        """
        # Ideally, we should add user_id to Chunk nodes too.
        # But if not, we can MATCH (c)-[:PART_OF]->(d:Document) WHERE d.user_id = $user_id
        # Vector index yield node first.
        query = """
        CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
        YIELD node, score
        MATCH (node)-[:PART_OF]->(d:Document)
        WHERE d.user_id = $user_id OR node.user_id = $user_id
        RETURN node.id as id, node.text as text, score
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, k=top_k * 2, embedding=embedding, user_id=user_id)
            nodes = []
            async for record in result:
                nodes.append(RetrievedNode(
                    id=record["id"] or "",
                    text=record["text"],
                    type="Chunk",
                    score=record["score"]
                ))
            return nodes

    async def _graph_traversal(self, driver, seed_ids: List[str], user_id: str) -> List[str]:
        """
        Path 2: Graph Traversal (1-hop neighbors)
        """
        if not seed_ids:
            return []
            
        # Find neighbors for these nodes (Bi-directional)
        query = """
        MATCH (n) WHERE elementId(n) IN $ids OR n.id IN $ids
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.user_id = $user_id
        RETURN startNode(r).name as start_name, endNode(r).name as end_name, 
               type(r) as rel_label, r.type as rel_prop, 
               m.text as text, m.description as description
        LIMIT 50
        """
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, ids=seed_ids, user_id=user_id)
            
            context_parts = []
            seen_rels = set()
            
            async for record in result:
                start_name = record["start_name"]
                end_name = record["end_name"]
                rel_label = record["rel_label"]
                rel_prop = record["rel_prop"]
                
                if not start_name or not end_name:
                    continue
                    
                rel = rel_prop if rel_prop else rel_label
                
                # Deduplicate based on string representation
                rel_str = f"{start_name} -- [{rel}] --> {end_name}"
                if rel_str not in seen_rels:
                    context_parts.append(rel_str)
                    seen_rels.add(rel_str)
            
            return context_parts

    async def _find_paths_to_user(self, driver, target_ids: List[str], user_id: str) -> List[str]:
        """
        New Method: Find paths between User entity and Retrieved Entities.
        This is the "Ego-Centric" retrieval step.
        """
        if not target_ids:
            return []
            
        # We assume the user node has label Entity or Person and property user_id.
        # We look for shortest paths up to 2 hops.
        # Neo4j Bug Fix: shortestPath fails if start and end nodes are the same.
        # We must filter out cases where u = target.
        # FIX: Broaden the definition of "User Node" to include common self-references.
        query = """
        MATCH (u:Entity {user_id: $user_id}) 
        WHERE u.type IN ['Person', 'User', 'Self'] 
           OR u.name IN ['用户', 'User', 'user', '我', '自己', 'Me', 'me', 'I', 'i']
        WITH u
        MATCH (target) WHERE (elementId(target) IN $ids OR target.id IN $ids) AND target <> u
        MATCH p = shortestPath((u)-[*..2]-(target))
        RETURN [x in nodes(p) | x.name] as node_names, 
               [r in relationships(p) | type(r)] as rel_types,
               [r in relationships(p) | r.type] as rel_props
        LIMIT 10
        """
        
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, ids=target_ids, user_id=user_id)
            
            paths = []
            async for record in result:
                node_names = record["node_names"]
                rel_types = record["rel_types"]
                rel_props = record["rel_props"]
                
                # Format path string: "User --[REL]--> Node"
                path_str = ""
                for i in range(len(rel_types)):
                    start = node_names[i]
                    end = node_names[i+1]
                    rel = rel_props[i] if rel_props[i] else rel_types[i]
                    
                    if i == 0:
                        path_str += f"{start} --[{rel}]--> {end}"
                    else:
                        path_str += f" --[{rel}]--> {end}"
                
                if path_str:
                    paths.append(path_str)
            
            return paths

    async def _subgraph_keyword_search(self, driver, keyword: str, user_id: str) -> List[str]:
        """
        Path 4: Subgraph Keyword Search (Safety Net)
        Searches the User's immediate neighborhood (2 hops) for nodes containing the keyword.
        This helps when vector search misses the specific node due to low score or noise.
        """
        if not keyword or len(keyword.strip()) < 2:
            return []
            
        query = """
        MATCH (u:Entity {user_id: $user_id}) 
        WHERE u.type IN ['Person', 'User', 'Self'] 
           OR u.name IN ['用户', 'User', 'user', '我', '自己', 'Me', 'me', 'I', 'i']
        MATCH p = (u)-[r*1..2]-(n)
        WHERE (toLower(n.name) CONTAINS toLower($keyword) OR toLower($keyword) CONTAINS toLower(n.name))
          AND n <> u
        RETURN [x in nodes(p) | x.name] as node_names, 
               [rel in relationships(p) | type(rel)] as rel_types,
               [rel in relationships(p) | rel.type] as rel_props
        LIMIT 5
        """
        
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            result = await session.run(query, user_id=user_id, keyword=keyword)
            
            paths = []
            seen_paths = set()
            
            async for record in result:
                node_names = record["node_names"]
                rel_types = record["rel_types"]
                rel_props = record["rel_props"]
                
                # Format path string
                path_str = ""
                for i in range(len(rel_types)):
                    start = node_names[i]
                    end = node_names[i+1]
                    rel = rel_props[i] if rel_props[i] else rel_types[i]
                    
                    if i == 0:
                        path_str += f"{start} --[{rel}]--> {end}"
                    else:
                        path_str += f" --[{rel}]--> {end}"
                
                if path_str and path_str not in seen_paths:
                    paths.append(path_str)
                    seen_paths.add(path_str)
            
            return paths

    async def search(self, query: str, user_id: str, top_k: int = 5) -> str:
        """
        Executes the full GraphRAG pipeline.
        """
        logger.info(f"GraphRAG Search for User {user_id}: {query}")
        
        # 1. Generate Embedding
        embedding = await self._get_embedding(query)
        
        driver = await Neo4jManager.get_driver()
        
        # 2. Parallel Vector Search (Path 1)
        task_entities = self._vector_search_entities(driver, embedding, user_id, top_k)
        task_chunks = self._vector_search_chunks(driver, embedding, user_id, top_k)
        
        results = await asyncio.gather(task_entities, task_chunks)
        entity_nodes, chunk_nodes = results
        
        all_nodes = entity_nodes + chunk_nodes
        # Sort by score
        all_nodes.sort(key=lambda x: x.score, reverse=True)
        top_nodes = all_nodes[:top_k]
        
        # Collect IDs for graph traversal
        seed_ids = [n.id for n in top_nodes if n.id]
        
        # 3. Graph Traversal (Path 2: Neighbors)
        neighbor_texts = await self._graph_traversal(driver, seed_ids, user_id)
        
        # 4. User Connection Discovery (Path 3: Ego-Centric from Search Results)
        user_paths = await self._find_paths_to_user(driver, seed_ids, user_id)
        
        # 5. Subgraph Keyword Search (Path 4: Safety Net)
        # Use the query as keyword (or extract entities if we had an extractor)
        # For "What is X?", X is usually in the query.
        subgraph_paths = await self._subgraph_keyword_search(driver, query, user_id)
        
        # 6. Context Construction
        context_list = []
        context_list.append("--- Retrieved Entities/Chunks ---")
        for node in top_nodes:
            context_list.append(f"[{node.type}] {node.text}")
        
        if user_paths or subgraph_paths:
            context_list.append("\n--- Direct Connection to User (Important!) ---")
            if user_paths:
                context_list.extend(user_paths)
            if subgraph_paths:
                # Deduplicate
                for p in subgraph_paths:
                    if p not in user_paths:
                        context_list.append(p)
            
        context_list.append("\n--- Graph Context (Neighbors) ---")
        context_list.extend(neighbor_texts)
        
        full_context = "\n".join(context_list)
        
        # 7. Rerank & Generation (LLM)
        logger.info(f"Generating answer with context length: {len(full_context)}")
        
        prompt = ChatPromptTemplate.from_template(
            """You are an intelligent assistant powered by a Knowledge Graph.
            Use the following context to answer the user's question. 
            PAY SPECIAL ATTENTION to the "Direct Connection to User" section.
            If the context shows a connection between the User and the topic (e.g., User --[HAS_BIRTHDAY]--> Date), 
            you MUST mention this personal fact in your answer.
            
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

