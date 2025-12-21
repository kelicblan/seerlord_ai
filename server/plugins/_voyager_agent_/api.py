from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage
import json
import asyncio

from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.plugins.voyager_agent.plugin import get_agent as get_voyager_agent

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    skill_used: str
    skill_level: str
    evolution_occurred: bool = False

@router.post("/chat", response_model=ChatResponse)
async def voyager_chat(request: ChatRequest):
    """
    Endpoint to interact with the Voyager Agent.
    It will automatically route to the best skill or evolve a new one.
    """
    try:
        # Convert history if needed (simplified here)
        messages = [HumanMessage(content=request.message)]
        
        # Initialize Voyager Agent
        agent = get_voyager_agent()
        
        # Run Agent
        # Note: In a real app, we'd manage state persistence
        result = await agent.ainvoke({
            "messages": messages,
            "current_skill": None, # Will be filled by retrieve_skill
            "skill_match_reason": "",
            "execution_result": ""
        })
        
        skill = result["current_skill"]
        execution_result = result["execution_result"]
        match_reason = result["skill_match_reason"]
        
        return ChatResponse(
            response=execution_result,
            skill_used=skill.name,
            skill_level=skill.level,
            evolution_occurred=("Evolved" in match_reason)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def voyager_stream(request: ChatRequest):
    """
    Streaming endpoint for Voyager Agent.
    Emits SSE events for:
    - skill_retrieved
    - skill_evolution_start
    - skill_evolved
    - token (if streaming LLM output, though current implementation might be block-based)
    - final_result
    """
    agent = get_voyager_agent()
    messages = [HumanMessage(content=request.message)]
    
    async def event_generator():
        try:
            async for event in agent.astream_events({
                "messages": messages,
                "current_skill": None,
                "skill_match_reason": "",
                "execution_result": ""
            }, version="v2"):
                
                event_type = event["event"]
                
                # Handle Custom Events (Skill System)
                if event_type == "on_custom_event":
                    data = {
                        "type": event["name"], # skill_retrieved, skill_evolved, etc.
                        "data": event["data"]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    
                # Handle Output (Final Result from nodes)
                # Note: Depending on graph structure, we might want to capture 'on_chain_end' of the main graph
                # or specifically the 'execute_task' node output.
                # For simplicity, we check if we have output in chain end events
                elif event_type == "on_chain_end" and event["name"] == "LangGraph":
                    # The top-level graph finished
                    output = event["data"].get("output")
                    if output and "execution_result" in output:
                        data = {
                            "type": "final_result",
                            "data": output["execution_result"]
                        }
                        yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
