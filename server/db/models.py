from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from server.db.session import Base

class SkillLevelEnum(str, enum.Enum):
    SPECIFIC = "specific"  # L1
    DOMAIN = "domain"      # L2
    META = "meta"          # L3

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, index=True) # e.g. "tenant-001"
    name = Column(String, index=True)
    api_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    skills = relationship("Skill", back_populates="tenant")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True, index=True) # Changed to String to match UUID
    name = Column(String, index=True)
    description = Column(Text)
    code = Column(Text) # Python source code (from content.code_logic)
    level = Column(String, default=SkillLevelEnum.SPECIFIC.value)
    
    content_json = Column(JSON) # Store full SkillContent and Stats
    
    tenant_id = Column(String, ForeignKey("tenants.id"))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="skills")

class DocumentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"))
    filename = Column(String)
    file_path = Column(String)
    status = Column(String, default=DocumentStatusEnum.PENDING.value)
    error_msg = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    events = relationship("DocumentEvent", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("documents.id"), index=True)
    chunk_index = Column(Integer, index=True)
    text = Column(Text)
    text_len = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

class DocumentEvent(Base):
    __tablename__ = "document_events"

    id = Column(String, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("documents.id"))
    event_type = Column(String, index=True)
    message = Column(Text)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="events")

class LLMModel(Base):
    __tablename__ = "llm_models"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider = Column(String, index=True) # openai, ollama
    name = Column(String, unique=True, index=True) # Display name
    base_url = Column(String, nullable=True)
    model_name = Column(String) # The actual model identifier string
    api_key = Column(String, nullable=True)
    model_type = Column(String, default="llm") # llm, embedding, reranker, text-to-image, text-to-video, voice
    price_per_1k_tokens = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    description = Column(String, nullable=True)
