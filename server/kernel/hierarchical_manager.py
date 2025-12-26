import json
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate

from server.core.config import settings
from server.memory.storage import VectorStoreManager
from server.memory.schemas import MemoryItem, MemoryType
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.core.llm import get_llm, get_embeddings

class HierarchicalSkillManager:
    """
    Manages the lifecycle, retrieval, and execution of hierarchical skills.
    Singleton.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HierarchicalSkillManager, cls).__new__(cls)
            cls._instance.storage = None
            cls._instance.embeddings = None
        return cls._instance

    async def initialize(self):
        """Ensure the VectorStore is ready."""
        self.storage = await VectorStoreManager.get_instance()
        self.embeddings = get_embeddings()

    async def add_skill(self, skill: HierarchicalSkill):
        """Save a skill to the vector store."""
        if not self.storage: await self.initialize()
        
        # We store the description as the vector for semantic search
        content_text = f"{skill.name}: {skill.description}"
        
        metadata = skill.to_payload()
        # Fix collision with MemoryItem's 'content' field if needed, 
        # but MemoryItem uses 'content' as the main text.
        # Here we want to store the structured skill data in metadata.
        
        # The 'content' in skill.to_payload() is the SkillContent object (dict).
        # We should rename it in metadata to avoid confusion with MemoryItem.content
        if "content" in metadata:
            metadata["_skill_content"] = metadata.pop("content")
        
        metadata["type"] = MemoryType.SKILL.value
        
        item = MemoryItem(
            content=content_text,
            type=MemoryType.SKILL,
            importance_score=1.0, # Skills are high importance
            metadata=metadata
        )
        
        await self.storage.add_documents([item])
        logger.info(f"Added skill: {skill.name} ({skill.level})")

    async def retrieve_best_skill(self, query: str, min_score: float = 0.80) -> Tuple[Optional[HierarchicalSkill], str]:
        """
        Implements the "Bottom-Up Fallback" routing logic.
        Returns: (Skill, MatchReason)
        """
        if not self.storage: await self.initialize()

        # 1. Generate Query Vector
        query_vector = await self.embeddings.aembed_query(query)

        # 2. Search for everything relevant
        results = await self.storage.search(
            query_vector=query_vector,
            limit=5,
            score_threshold=min_score,
            filter_dict={"type": MemoryType.SKILL.value}
        )
        
        skills: List[HierarchicalSkill] = []
        for item in results:
            try:
                # Reconstruct skill object
                s_data = item.metadata.copy()
                
                # Restore content
                if "_skill_content" in s_data:
                    s_data["content"] = s_data.pop("_skill_content")
                    
                # Remove Qdrant specific fields if any
                if "type" in s_data: del s_data["type"]
                
                # We need to ensure 'content' is a dict compatible with SkillContent
                # In to_payload(), it might be serialized? Assuming it's a dict.
                
                skill = HierarchicalSkill.model_validate(s_data)
                skills.append(skill)
            except Exception as e:
                logger.error(f"Failed to parse skill: {e}")

        if not skills:
            # Fallback to hardcoded L3 if nothing found
            return self._get_default_meta_skill(), "Fallback to Default Meta"

        # 3. Priority Logic: L1 > L2 > L3
        # Sort by Level (Specific first) and then Score
        # But since we don't have score in the object, we rely on retrieval order (mostly sorted by score)
        
        # Let's filter by levels
        l1_skills = [s for s in skills if s.level == SkillLevel.SPECIFIC]
        l2_skills = [s for s in skills if s.level == SkillLevel.DOMAIN]
        l3_skills = [s for s in skills if s.level == SkillLevel.META]

        if l1_skills:
            return l1_skills[0], "Matched Specific Skill"
        
        if l2_skills:
            return l2_skills[0], "Fallback to Domain Skill"
            
        if l3_skills:
            return l3_skills[0], "Fallback to Meta Skill"

        return self._get_default_meta_skill(), "Fallback to Default Meta"

    def _get_default_meta_skill(self) -> HierarchicalSkill:
        """Returns the built-in General Learning Skill (L3)."""
        return HierarchicalSkill(
            name="GeneralLearning",
            description="A meta-skill for learning any new topic by breaking it down.",
            level=SkillLevel.META,
            content=SkillContent(
                prompt_template="""You are a universal tutor. The user wants to learn about: {topic}.
Strategy:
1. Explain the core concept simply (Feynman technique).
2. Provide 3 key pillars of this topic.
3. Suggest a practical exercise.
""",
                knowledge_base=["Feynman Technique", "First Principles Thinking"]
            )
        )

    async def execute_skill(self, skill: HierarchicalSkill, user_input: str) -> str:
        """
        Executes the skill using LLM.
        """
        logger.info(f"Executing Skill: {skill.name} ({skill.level})")
        
        llm = get_llm()
        
        # 1. Prepare Prompt
        # We need to extract variables from user input if the prompt template has slots
        # For simplicity, we assume a simple {topic} or just append user input
        
        system_prompt = skill.content.prompt_template
        
        # If it's a domain skill, we might need to extract the specific subject
        # e.g., "Learn German" -> Subject="German"
        
        messages = [
            ("system", system_prompt),
            ("human", user_input)
        ]
        
        response = await llm.ainvoke(messages)
        
        # Update stats (simple increment)
        skill.stats.success_count += 1
        skill.stats.last_used = datetime.now()
        # TODO: Persist stats update
        
        return response.content

hierarchical_manager = HierarchicalSkillManager()
