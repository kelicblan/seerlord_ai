from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from .schema import TutorialSchema

# 定义局部状态
class TutorialState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # Context
    tenant_id: str
    user_id: str
    
    tutorial_result: Optional[TutorialSchema]
    detailed_content: Optional[str] # Store the final generated content
    critique_count: int
    score: int
    critique_feedback: str
    
    # Track used skills for feedback
    used_skill_ids: List[str]
