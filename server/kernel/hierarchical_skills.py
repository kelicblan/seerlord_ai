from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

GLOBAL_SKILL_TENANT_ID = "global"

class SkillLevel(str, Enum):
    SPECIFIC = "specific"   # L1: 具体技能 (e.g., LearnEnglish)
    DOMAIN = "domain"       # L2: 领域技能 (e.g., LearnLanguage)
    META = "meta"           # L3: 元技能 (e.g., GeneralLearning)

class SkillContent(BaseModel):
    """技能的具体内容"""
    prompt_template: str = Field(description="The prompt template for this skill.")
    knowledge_base: List[str] = Field(default_factory=list, description="List of knowledge points or rules.")
    code_logic: Optional[str] = Field(default=None, description="Optional Python code logic.")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for expected parameters.")

class UsageStats(BaseModel):
    """技能使用统计"""
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

class HierarchicalSkill(BaseModel):
    """分层技能模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Unique name of the skill")
    description: str = Field(description="Description for semantic search")
    level: SkillLevel
    parent_id: Optional[str] = Field(default=None, description="ID of the parent skill (L2/L3)")
    
    content: SkillContent
    stats: UsageStats = Field(default_factory=UsageStats)
    
    # Metadata for vector store filtering
    tags: List[str] = Field(default_factory=list)

    def to_payload(self) -> Dict[str, Any]:
        """Convert to payload for Qdrant storage."""
        return self.model_dump(mode='json')
