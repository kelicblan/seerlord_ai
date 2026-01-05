from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

class PPTGeneratorState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tenant_id: str
    user_id: str
    memory_context: str
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
