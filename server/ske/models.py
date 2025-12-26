from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class RelationshipType(str, Enum):
    """
    Neo4j Relationship Types
    """
    MENTIONS = "MENTIONS"       # (:Chunk)-[:MENTIONS]->(:Entity)
    RELATED_TO = "RELATED_TO"   # (:Entity)-[:RELATED_TO]->(:Entity)
    GENERATED = "GENERATED"     # (:AgentSession)-[:GENERATED]->(:Entity)

class BaseGraphNode(BaseModel):
    """
    Base class for all graph nodes
    """
    id: Optional[str] = Field(None, description="Unique identifier (UUID or Neo4j elementId)")

class EntityNode(BaseGraphNode):
    """
    Represents a business entity in the Knowledge Graph.
    Everything has an Embedding.
    """
    name: str = Field(..., description="Name of the entity")
    type: str = Field(..., description="Type of the entity (e.g., Person, Organization)")
    description: Optional[str] = Field(None, description="Description of the entity")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the entity")
    
    # Allow extra fields for dynamic properties
    model_config = {"extra": "allow"}

class DocumentNode(BaseGraphNode):
    """
    Represents an original document file.
    """
    filename: str = Field(..., description="Name of the source file")
    upload_date: datetime = Field(default_factory=datetime.now, description="When the document was uploaded")

class ChunkNode(BaseGraphNode):
    """
    Represents a text chunk from a document.
    """
    text: str = Field(..., description="The content of the text chunk")
    index: int = Field(..., description="Index of the chunk in the document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the chunk text")

class AgentSessionNode(BaseGraphNode):
    """
    Represents an Agent execution session for traceability.
    """
    session_id: str = Field(..., description="Unique session ID")
    agent_name: str = Field(..., description="Name of the agent")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
