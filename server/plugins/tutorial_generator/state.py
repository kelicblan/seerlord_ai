from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from .schema import TutorialSchema, CourseOutline, OfflineCoursePackage

# 定义局部状态
class TutorialState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # Context
    tenant_id: str
    user_id: str
    memory_context: str
    skills_context: Optional[str]
    
    tutorial_result: Optional[TutorialSchema]
    detailed_content: Optional[str] # Store the final generated content
    critique_count: int
    score: int
    critique_feedback: str
    
    # Track used skills for feedback
    used_skill_ids: List[str]

    export_id: Optional[str]
    export_download_url: Optional[str]
    course_outline: Optional[CourseOutline]
    course_package: Optional[Dict[str, Any]]
