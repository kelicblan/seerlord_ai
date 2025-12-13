from typing import List, Optional
from pydantic import BaseModel, Field

class ResearchTask(BaseModel):
    """Local plan step."""
    id: int = Field(description="Task ID")
    action: str = Field(description="Action type: 'search', 'read', 'summarize'")
    query: str = Field(description="Search query or content to process")
    rationale: str = Field(description="Why this step is needed")

class ResearchPlan(BaseModel):
    """Local execution plan."""
    tasks: List[ResearchTask] = Field(description="List of research tasks")

class Reflection(BaseModel):
    """Critique result."""
    is_satisfactory: bool = Field(description="Is the result good enough?")
    feedback: str = Field(description="Feedback for improvement")
    missing_info: List[str] = Field(description="List of missing information points")
