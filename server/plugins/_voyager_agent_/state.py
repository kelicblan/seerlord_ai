from typing import List, TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from server.kernel.hierarchical_skills import HierarchicalSkill

class VoyagerState(TypedDict):
    # Standard LangGraph state
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Context
    tenant_id: str
    user_id: str
    memory_context: str
    
    # Voyager specific
    current_skill: HierarchicalSkill
    skill_match_reason: str
    execution_result: str
    
    # Optimization
    needs_refinement: bool
    critic_feedback: str
