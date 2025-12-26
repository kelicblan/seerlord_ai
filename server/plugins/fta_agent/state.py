from typing import Annotated, List, Literal, Optional, Union
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class FTANode(BaseModel):
    """故障树节点"""
    id: str = Field(description="Unique ID of the node")
    label: str = Field(description="Description of the event")
    type: str = Field(description="Type: 'top_event', 'intermediate', 'basic_event'")
    parent_id: Optional[str] = Field(default=None, description="ID of the parent node")
    gate: Optional[str] = Field(default="OR", description="Logic gate to children (OR/AND)")

class FTAState(TypedDict):
    """FTA 分析的状态"""
    messages: Annotated[List[BaseMessage], add_messages]
    # Context
    tenant_id: str
    user_id: str
    memory_context: str
    
    tree_nodes: List[FTANode]
    processing_queue: List[str] # 待分析的节点 ID 列表
    completed: bool
    iteration_count: int
    critique_count: int
    score: int
    critique_feedback: str
