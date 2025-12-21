from typing import List, Optional, Dict, Any, TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from server.kernel.hierarchical_skills import HierarchicalSkill

class EvolverState(TypedDict):
    # Context
    tenant_id: str
    user_id: str
    
    # Input
    task: str # e.g. "analyze_failure", "refine_skill"
    conversation_history: List[BaseMessage]
    related_skills: List[HierarchicalSkill]
    
    # Internal
    reasoning_log: List[str]
    
    # Output
    proposed_skill: Optional[HierarchicalSkill]
    evolution_report: str
