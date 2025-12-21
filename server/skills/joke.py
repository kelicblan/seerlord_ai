from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.kernel.hierarchical_manager import HierarchicalSkillManager
from loguru import logger

def create_joke_skill() -> HierarchicalSkill:
    """
    创建“讲笑话”技能的结构化定义。
    """
    return HierarchicalSkill(
        name="TellJoke",
        description="Generates a funny joke based on a topic or context.",
        level=SkillLevel.SPECIFIC,
        content=SkillContent(
            prompt_template="""You are a professional comedian.
            Task: Tell a joke about {topic}.
            Style: Witty, family-friendly, and clever.
            Rules:
            - Keep it under 50 words.
            - Do not explain the joke.
            """,
            knowledge_base=[
                "Timing is everything.",
                "Puns are the lowest form of humor, but acceptable if clever."
            ],
            parameters_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The topic of the joke"}
                },
                "required": ["topic"]
            }
        ),
        tags=["fun", "entertainment"]
    )

async def register_joke_skill():
    """
    将“讲笑话”技能写入技能库（向量数据库）。
    """
    manager = HierarchicalSkillManager()
    skill = create_joke_skill()
    await manager.add_skill(skill)
    logger.info(f"技能注册成功：{skill.name}")

if __name__ == "__main__":
    import asyncio
    from server.kernel.memory_manager import memory_manager
    
    async def main():
        await memory_manager.initialize()
        await register_joke_skill()
        await memory_manager.close()
        
    asyncio.run(main())
