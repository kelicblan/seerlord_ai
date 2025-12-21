
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime

# --- Data Models (Mirroring Frontend Skill Structure) ---

class SkillEvolutionRecord(BaseModel):
    """Record of a single evolution/update event for a skill."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp() * 1000)
    agent_id: str  # Which agent triggered this (e.g., 'tutorial_generator', 'skill_evolver')
    change_description: str
    diff: Optional[str] = None  # Text diff or JSON diff
    version: int  # Version number

class Skill(BaseModel):
    id: str
    name: str
    description: str
    category: str
    level: int  # 1: Specific, 2: Domain, 3: Meta
    parentId: Optional[str] = None
    content: str  # The Prompt/Instruction
    tags: List[str] = []
    history: List[SkillEvolutionRecord] = []  # Evolution History
    version: int = 1

# --- Mock Data Service ---

class SkillService:
    def __init__(self):
        # Initialize with the same mock data as in Frontend (SkillManage.vue)
        self.skills: List[Skill] = [
             # L3: 元技能
            Skill(
                id='101',
                name='学习方法',
                description='元认知学习策略 (L3) - 如何高效学习任何知识',
                category='tutorial_agent',
                level=3,
                content="""[SYSTEM: META_INSTRUCTION]
你现在不是一个百科全书，你是一个苏格拉底式的导师。
你的核心目标不是“灌输信息”，而是“引导发现”。
1. 不要直接给答案，要先用一个生活中的类比（Analogy）。
2. 必须检查用户的认知偏差。
3. 所有的解释必须遵循：What（是什么） -> Why（为什么学） -> How（怎么做）。""",
                tags=['meta-learning', 'cognition'],
                history=[
                    SkillEvolutionRecord(
                        skill_id='101',
                        agent_id='system_init',
                        change_description='Initial creation of Meta Strategy',
                        timestamp=datetime.now().timestamp() * 1000 - 1000000,
                        version=1
                    )
                ]
            ),
             # L2: 领域技能 (父级: 学习方法)
            Skill(
                id='102',
                name='学语言',
                description='语言习得通用模式 (L2) - 词汇/语法/听说的通用训练法',
                category='tutorial_agent',
                level=2,
                parentId='101',
                content="""[SYSTEM: DOMAIN_PATTERN_LANGUAGE]
你正在教授语言知识。
输出格式必须严格遵守以下 JSON 结构（方便前端渲染代码块）：
{
  "concept": "概念名称",
  "analogy": "用物理世界的机械结构做类比",
  "code_example": "一段不超过 10 行的最小可运行代码",
  "pitfall": "新手最容易犯的一个错误（比如死循环）",
  "exercise": "一个填空题"
}
Components:
- Vocabulary: Spaced Repetition System
- Grammar: Pattern Recognition
- Listening: Immersion
- Speaking: Shadowing""",
                tags=['language-acquisition'],
                history=[]
            ),
            # L1: 具体技能 (父级: 学语言)
            Skill(
                id='103',
                name='学英语',
                description='英语具体语法与词汇 (L1) - 针对英语特性的训练',
                category='tutorial_agent',
                level=1,
                parentId='102',
                content="""[SYSTEM: SPECIFIC_SKILL_ENGLISH]
- Focus: SVO structure, Tenses, Articles
- Resources: Oxford 3000, BBC Learning English
- Practice: Daily conversation with AI""",
                tags=['english'],
                history=[]
            ),
             # 模拟进化机制派生的新技能
             Skill(
                id='104',
                name='学德语',
                description='德语基础入门 (L1) - 由"学语言"派生',
                category='tutorial_agent',
                level=1,
                parentId='102',
                content="""[Specific-Skill: German]
- Focus: Cases (Nominative, Accusative, Dative, Genitive), Genders
- Resources: DW Deutsch, Nicos Weg""",
                tags=['german', 'derived'],
                history=[
                    SkillEvolutionRecord(
                        skill_id='104',
                        agent_id='skill_evolver',
                        change_description='Derived from "学语言" pattern',
                        timestamp=datetime.now().timestamp() * 1000 - 500000,
                        version=1
                    )
                ]
            ),
             # 编程相关的 L1 技能 (假设补充)
            Skill(
                id='201',
                name='Python 循环',
                description='Python For Loop 教学',
                category='tutorial_agent',
                level=1,
                parentId='101', # 暂时挂在 L3 下，实际应该有 Coding L2
                content="""[SYSTEM: SPECIFIC_TOPIC_PYTHON_FOR_LOOP]
你在讲 Python 的 for 循环。
1. 最佳类比：不要用“迭代器”，要用“工厂流水线”或“点名册”来比喻。
2. 强调重点：for item in list，这里的 item 是一个临时变量，就像流水线上的机械手拿到的当前零件。
3. 禁忌：在这个阶段绝对不要提 while 循环，以免混淆。""",
                tags=['python', 'coding'],
                history=[]
            )
        ]

    def get_skill_by_id(self, skill_id: str) -> Optional[Skill]:
        return next((s for s in self.skills if s.id == skill_id), None)

    def log_evolution(self, skill_id: str, agent_id: str, change_desc: str, new_content: str):
        skill = self.get_skill_by_id(skill_id)
        if not skill:
            return
        
        # Calculate fake diff for demo
        diff = f"Changed content length from {len(skill.content)} to {len(new_content)}"
        
        skill.content = new_content
        skill.version += 1
        
        record = SkillEvolutionRecord(
            skill_id=skill_id,
            agent_id=agent_id,
            change_description=change_desc,
            diff=diff,
            version=skill.version
        )
        skill.history.insert(0, record) # Newest first

    def get_skills_by_category(self, category: str) -> List[Skill]:
        return [s for s in self.skills if s.category == category]

    def retrieve_skills_for_query(self, query: str, category: str = 'tutorial_agent') -> List[Skill]:
        """
        Simple keyword-based retrieval for demonstration.
        In a real system, this would use vector similarity search (RAG).
        """
        candidates = self.get_skills_by_category(category)
        matched_skills = []
        
        # 1. 强制包含 L3 元技能 (Always Active for this Agent)
        meta_skills = [s for s in candidates if s.level == 3]
        matched_skills.extend(meta_skills)

        # 2. 简单的关键词匹配 L1/L2
        query_lower = query.lower()
        for skill in candidates:
            if skill.level < 3:
                # 如果查询中包含技能名或标签，则召回
                if skill.name.lower() in query_lower or any(tag in query_lower for tag in skill.tags):
                    matched_skills.append(skill)
                    
                    # 3. 如果召回了 L1，自动召回其父级 L2 (Chain of Skills)
                    if skill.parentId:
                        parent = next((s for s in candidates if s.id == skill.parentId), None)
                        if parent and parent not in matched_skills:
                            matched_skills.append(parent)
        
        # Deduplicate
        unique_skills = {s.id: s for s in matched_skills}.values()
        
        # Sort by Level (L3 -> L2 -> L1) for Prompt Ordering
        return sorted(unique_skills, key=lambda s: s.level, reverse=True)

# Singleton Instance
skill_service = SkillService()
