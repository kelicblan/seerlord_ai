from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from server.core.database import Base
from datetime import datetime

class AutomationTask(Base):
    __tablename__ = "automation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=True)
    agent_id = Column(String, nullable=False)
    input_prompt = Column(Text, nullable=True)
    
    # Timing configuration
    # If cron_expression is present, it takes precedence over interval_seconds
    cron_expression = Column(String, nullable=True)  # e.g. "0 12 * * *"
    interval_seconds = Column(Integer, nullable=True)
    
    is_one_time = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    next_run_time = Column(DateTime, nullable=True)
    last_run_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, index=True)
    status = Column(String)  # RUNNING, SUCCESS, FAILURE
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
