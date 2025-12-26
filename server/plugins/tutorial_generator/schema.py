from typing import List, Optional, Dict
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

class LessonOutline(BaseModel):
    id: str = Field(description="课时唯一 ID")
    title: str = Field(description="课时标题")
    objective: str = Field(description="课时学习目标")
    estimated_minutes: int = Field(description="预计学习分钟数")
    checkpoint_required: bool = Field(default=True, description="是否需要成果校验")

class CourseModuleOutline(BaseModel):
    title: str = Field(description="模块标题")
    goal: str = Field(description="模块目标")
    lessons: List[LessonOutline] = Field(description="模块课时列表")

class CourseOutline(BaseModel):
    title: str = Field(description="课程标题")
    topic: str = Field(description="学习主题")
    target_audience: str = Field(description="目标人群/基础假设")
    prerequisites: List[str] = Field(default_factory=list, description="先修知识")
    total_estimated_hours: float = Field(description="总预计学习小时数")
    modules: List[CourseModuleOutline] = Field(description="课程模块列表")

class ExerciseItem(BaseModel):
    prompt: str = Field(description="练习题目")
    hints: List[str] = Field(default_factory=list, description="提示")
    expected: str = Field(description="期望要点/结果")

class MCQQuestion(BaseModel):
    question: str = Field(description="选择题题干")
    options: List[str] = Field(description="选项列表")
    answer_index: int = Field(description="正确选项索引，从 0 开始")
    rationale: str = Field(description="正确答案解释")

class ShortAnswerQuestion(BaseModel):
    question: str = Field(description="简答题题干")
    key_points: List[str] = Field(default_factory=list, description="参考要点")
    rubric: List[str] = Field(default_factory=list, description="评分标准/检查清单")

class LessonCheckpoint(BaseModel):
    pass_score: int = Field(default=70, description="及格分，0-100")
    mcq: List[MCQQuestion] = Field(default_factory=list, description="选择题列表")
    short_answer: List[ShortAnswerQuestion] = Field(default_factory=list, description="简答题列表")

class LessonContent(BaseModel):
    id: str = Field(description="课时 ID，与大纲一致")
    title: str = Field(description="课时标题")
    image_prompt: Optional[str] = Field(None, description="用于生成课时插图的提示词")
    image_base64: Optional[str] = Field(None, description="课时插图的 Base64 数据")
    feynman_analogy: str = Field(description="类比解释（费曼风格）")
    plain_explanation: str = Field(description="给 12 岁孩子的白话解释")
    key_terms: List[str] = Field(default_factory=list, description="关键术语")
    common_misconceptions: List[str] = Field(default_factory=list, description="常见误解与纠偏")
    examples: List[str] = Field(default_factory=list, description="例子列表")
    exercises: List[ExerciseItem] = Field(default_factory=list, description="练习列表")
    checkpoint: LessonCheckpoint = Field(default_factory=LessonCheckpoint, description="成果校验")

class OfflineCoursePackage(BaseModel):
    export_id: str = Field(description="导出包 ID")
    outline: CourseOutline = Field(description="课程大纲")
    lessons: Dict[str, LessonContent] = Field(default_factory=dict, description="lesson_id -> 内容")
    generated_at: str = Field(description="生成时间 ISO 字符串")
