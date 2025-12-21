from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from server.core.database import Base

class LLMTrace(Base):
    __tablename__ = "llm_traces"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True) # The LangChain run_id
    session_id = Column(String, index=True, nullable=True) # The thread_id
    tenant_id = Column(String, index=True, nullable=True)
    user_id = Column(String, index=True, nullable=True)
    
    model_name = Column(String, nullable=True)
    prompts = Column(JSON, nullable=True) # Storing the list of prompts/messages
    outputs = Column(JSON, nullable=True) # Storing the generation output
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    error = Column(String, nullable=True)
