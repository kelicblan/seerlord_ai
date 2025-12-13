from typing import List, Optional
from pydantic import BaseModel, Field

class Module(BaseModel):
    """教程模块"""
    name: str = Field(description="模块名称")
    topics: List[str] = Field(description="模块涵盖的主题列表")

class TutorialSchema(BaseModel):
    """教程结构化模式"""
    title: str = Field(description="教程的标题")
    difficulty: str = Field(description="教程难度级别 (Beginner, Intermediate, Advanced)")
    modules: List[Module] = Field(description="教程包含的模块列表")
    summary: Optional[str] = Field(description="教程的简短摘要")
