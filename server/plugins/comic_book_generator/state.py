from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from .schema import ComicBook, CourseSyllabus

class ComicState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Context
    tenant_id: str
    user_id: str
    skills_context: Optional[str]
    
    # Intermediate State
    syllabus: Optional[CourseSyllabus]
    comic_script: Optional[ComicBook]
    image_map: Optional[Dict[int, str]] # page_number -> local file path
    
    # Final Output
    pdf_file_path: Optional[str]
    download_url: Optional[str]
    
    # Feedback / Metrics
    used_skill_ids: List[str]
