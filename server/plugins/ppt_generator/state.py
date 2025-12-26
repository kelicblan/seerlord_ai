from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

class PPTGeneratorState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tenant_id: str
    user_id: str
    memory_context: str
