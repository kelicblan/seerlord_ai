# LangGraph State definition
# For Config-based agents, this might be implicit or generic.
from typing_extensions import TypedDict
from typing import Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class NewsReporterState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # Add other state fields if needed
