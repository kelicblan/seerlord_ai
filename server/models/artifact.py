from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Integer
from sqlalchemy.sql import func
from server.db.session import Base

class AgentArtifact(Base):
    __tablename__ = "agent_artifacts"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)
    agent_id = Column(String, index=True, nullable=False)
    execution_id = Column(String, index=True, nullable=True)
    
    # type: 'file' or 'content'
    type = Column(String, nullable=False)
    
    # value: file path or text content
    value = Column(Text, nullable=False)
    
    # Metadata for UI
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    total_tokens = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
