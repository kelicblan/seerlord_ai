from typing import TypedDict, List, Annotated, Optional
import operator
from langchain_core.messages import BaseMessage

class NewsState(TypedDict):
    """
    State for the News Reporter agent.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Context fields
    tenant_id: str
    user_id: str
    memory_context: str
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
    agent_description: Optional[str]  # Added for skill evolution context
    
    # Plugin specific fields
    search_query: Optional[str] # The generated search query
    news_content: str
    latest_summary: str
