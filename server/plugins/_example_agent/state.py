from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from .schema import ResearchPlan

class ExampleState(TypedDict):
    """
    State for the Example Agent (Research Assistant).
    """
    # Standard message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Context
    tenant_id: str
    user_id: str
    
    # Inputs
    user_topic: str
    
    # Planning
    local_plan: Optional[ResearchPlan]
    current_task_index: int
    
    # Execution
    collected_info: List[str] # List of gathered snippets
    
    # Critique
    critique_count: int
    feedback_history: List[str]
    
    # Output
    final_report: str
