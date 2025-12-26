from typing import List, Optional, Tuple
from loguru import logger
from langchain_core.messages import HumanMessage
from langchain_core.callbacks.manager import adispatch_custom_event

from server.kernel.skill_manager_sql import SQLSkillManager
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel
from server.plugins._skill_evolver_.plugin import get_agent as get_evolver_agent

class DynamicSkillManager:
    """
    Orchestrates skill retrieval, execution, and autonomous evolution.
    Uses SQLSkillManager for persistence (PostgreSQL + ChromaDB).
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DynamicSkillManager, cls).__new__(cls)
            cls._instance.skill_manager = SQLSkillManager()
            cls._instance.evolver_app = get_evolver_agent()
        return cls._instance

    async def get_or_evolve_skill(self, query: str, tenant_id: str, user_id: str = None, agent_name: str = "system_skill_manager", conversation_history: List = None) -> Tuple[HierarchicalSkill, str]:
        """
        Main logic:
        1. Try to find a Specific (L1) or Domain (L2) skill using SQLSkillManager.
        2. If only Meta (L3) is found (fallback), trigger Evolution.
        3. If evolution succeeds, persist the new skill to SQL/Chroma.
        4. Return the best available skill.
        """
        logger.info(f"🔍 Searching skill for query: '{query}' (Tenant: {tenant_id}, User: {user_id}, Agent: {agent_name})")
        
        # 1. Retrieval
        best_skill, reason = await self.skill_manager.retrieve_best_skill(query, tenant_id=tenant_id, user_id=user_id, agent_name=agent_name)
        logger.info(f"✅ Found: {best_skill.name} ({best_skill.level}) - {reason}")
        
        await adispatch_custom_event(
            "skill_retrieved", 
            {
                "name": best_skill.name,
                "level": best_skill.level.value,
                "reason": reason
            }
        )
        
        # 2. Check if Evolution is needed
        # Condition: If we fell back to Meta (L3) or Default, it means we lack specific skills.
        if best_skill.level == SkillLevel.META:
            logger.info("⚠️ Only Meta skill found. Triggering Evolution...")
            
            await adispatch_custom_event("skill_evolution_start", {"query": query})
            
            # Prepare context for Evolver
            evolver_input = {
                "task": query,
                "conversation_history": conversation_history or [HumanMessage(content=query)],
                "related_skills": [best_skill], # Pass the meta skill as context
                "reasoning_log": []
            }
            
            # Run Evolver
            try:
                result = await self.evolver_app.ainvoke(evolver_input)
                new_skill = result.get("proposed_skill")
                
                if new_skill:
                    logger.info(f"🧬 Evolution Complete! Created new skill: {new_skill.name} ({new_skill.level})")
                    
                    # 3. Persist the new skill!
                    await self.skill_manager.add_skill(new_skill, tenant_id=tenant_id, user_id=user_id)
                    
                    await adispatch_custom_event(
                        "skill_evolved",
                        {
                            "name": new_skill.name,
                            "level": new_skill.level.value,
                            "description": new_skill.description
                        }
                    )
                    
                    return new_skill, "Evolved New Skill"
                else:
                    logger.warning(f"🧬 Evolution failed: {result.get('evolution_report')}")
            except Exception as e:
                logger.error(f"❌ Evolution error: {e}")
                
        return best_skill, reason

# Global instance
dynamic_skill_manager = DynamicSkillManager()
