from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class MemoryType(str, Enum):
    EPISODIC = "episodic"       # 短期交互/对话片段
    SEMANTIC = "semantic"       # 长期事实/知识/偏好
    USER_PROFILE = "user_profile" # 用户画像/元数据
    SKILL = "skill"             # 技能/工具描述

class MemoryItem(BaseModel):
    """
    基础记忆单元，用于存入向量数据库
    """
    id: UUID = Field(default_factory=uuid4, description="唯一标识符")
    content: str = Field(..., description="记忆的文本内容")
    vector: Optional[List[float]] = Field(default=None, description="向量嵌入（可选，通常由存储层自动生成）")
    type: MemoryType = Field(..., description="记忆类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="记忆创建或相关的时间戳")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性评分 (0-1)，决定记忆保留优先级")
    similarity: Optional[float] = Field(default=None, description="向量相似度评分 (检索时动态生成)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据，如 source_conversation_id, tags, agent_id 等")

    class Config:
        use_enum_values = True

class UserProfile(BaseModel):
    """
    结构化用户画像
    """
    name: Optional[str] = Field(None, description="用户姓名或称呼")
    language: str = Field("zh-CN", description="用户首选语言")
    professional_background: Optional[str] = Field(None, description="职业背景")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    communication_style: Optional[str] = Field(None, description="沟通风格 (e.g., formal, casual, concise)")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="其他自定义属性")
