from typing import Annotated, List, Optional, TypedDict
from pydantic import BaseModel, Field
import operator

class SkeAgentState(TypedDict):
    """
    State for the SKE GraphRAG Agent.
    """
    question: str
    context: Annotated[List[str], operator.add]
    answer: Optional[str]
    # Keep track of search results for debug/citations
    search_results: List[dict]
