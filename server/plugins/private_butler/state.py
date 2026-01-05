from typing import TypedDict, List, Annotated, Optional, Dict, Any
import operator
from langchain_core.messages import BaseMessage

class ButlerState(TypedDict):
    """
    State for the Private Butler Agent.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    
    # User Context
    tenant_id: str
    user_id: str
    memory_context: Optional[str]
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
    
    # Intent Classification
    # MEMORY_WRITE, MEMORY_READ, TASK_EXECUTION, PROACTIVE_CHECK, CHITCHAT
    user_intent: Optional[str] 
    
    # Working Context (Time, Location, etc.)
    current_time: Optional[str]
    location: Optional[str]
    
    # Execution State
    plan: Optional[List[str]]
    tool_outputs: Optional[Dict[str, Any]]
    
    # Proactive State
    daily_briefing: Optional[str]
    
    # Feedback
    feedback: Optional[str]
