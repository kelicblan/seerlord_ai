from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class RequirementAnalystState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    input_file_path: Optional[str]
    parsed_content: Optional[str]
    doc1_content: Optional[str]
    doc2_content: Optional[str]
    doc1_path: Optional[str]
    doc2_path: Optional[str]
    tenant_id: str
    user_id: str
    memory_context: str
    total_tokens: int
