from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from server.ske.agent.workflow import ske_agent
from server.ske.database import Neo4jManager
from server.ske.ingestion import process_document
from server.ske.search import SkeSearchService
from server.api.v1.login import get_current_user
from server.models.user import User

router = APIRouter()

# --- Models ---

class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class IngestRequest(BaseModel):
    file_path: str

class GraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]

# --- Routes ---

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with the SKE Agent.
    """
    initial_state = {
        "question": request.message,
        "context": [],
        "answer": None,
        "search_results": []
    }
    
    try:
        # TODO: Implement streaming response if request.stream is True
        result = await ske_agent.ainvoke(initial_state)
        return {
            "answer": result.get("answer"),
            "search_results": result.get("search_results")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search(request: SearchRequest):
    """
    Perform hybrid search.
    """
    try:
        results = await SkeSearchService.search(request.query, request.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest(request: IngestRequest):
    """
    Trigger document ingestion.
    """
    try:
        # In a real app, you might want to run this in BackgroundTasks
        await process_document(request.file_path)
        return {"status": "success", "message": f"Processed {request.file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from neo4j.time import DateTime, Date

def normalize_value(value):
    if isinstance(value, (DateTime, Date)):
        return value.iso_format()
    return value

def normalize_props(props: Dict[str, Any]) -> Dict[str, Any]:
    new_props = {}
    for k, v in props.items():
        if k == "embedding":
            continue
        new_props[k] = normalize_value(v)
    return new_props

@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get graph data for visualization.
    """
    driver = await Neo4jManager.get_driver()
    # Filter nodes by user_id to ensure data isolation
    query = f"""
    MATCH (n)-[r]->(m)
    WHERE n.user_id = $user_id AND m.user_id = $user_id
    RETURN n, r, m
    LIMIT {limit}
    """
    
    nodes = {}
    links = []
    
    async with driver.session() as session:
        result = await session.run(query, user_id=str(current_user.id))
        async for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]
            
            # Process Node N
            n_id = n.element_id # Neo4j 5.x uses element_id
            if n_id not in nodes:
                nodes[n_id] = {
                    "id": n_id,
                    "labels": list(n.labels),
                    "properties": normalize_props(dict(n)),
                    "name": n.get("name") or n.get("id", "Unknown")
                }
            
            # Process Node M
            m_id = m.element_id
            if m_id not in nodes:
                nodes[m_id] = {
                    "id": m_id,
                    "labels": list(m.labels),
                    "properties": normalize_props(dict(m)),
                    "name": m.get("name") or m.get("id", "Unknown")
                }
            
            # Process Relationship
            links.append({
                "source": n_id,
                "target": m_id,
                "type": r.type,
                "properties": normalize_props(dict(r))
            })
            
    return {
        "nodes": list(nodes.values()),
        "links": links
    }
