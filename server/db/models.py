from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum, JSON
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
