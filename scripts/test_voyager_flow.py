import asyncio
import sys
import os
from loguru import logger

# Add project root to path
sys.path.append(os.getcwd())

from server.core.config import settings
from server.kernel.memory_manager import memory_manager
from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.kernel.hierarchical_skills import SkillLevel

async def test_evolution_flow():
    """
    Test the full Voyager loop:
    1. Query for unknown skill
    2. Trigger Evolution
    3. Verify new skill creation
    """
    logger.info("Initializing system...")
    await memory_manager.initialize()
    
    if not memory_manager.enabled:
        logger.error("Memory disabled. skipping.")
        return

    query = "I need to calculate the area of a circle with radius 5."
    logger.info(f"\n--- Step 1: Querying for unknown skill: '{query}' ---")
    
    # This should trigger evolution because we don't have a specific skill for Math/Geometry yet
    # (Assuming the DB only has the language skills from previous test)
    
    skill, reason = await dynamic_skill_manager.get_or_evolve_skill(query)
    
    logger.info(f"Result: {skill.name} ({skill.level})")
    logger.info(f"Reason: {reason}")
    
    if reason == "Evolved New Skill":
        logger.info("✅ SUCCESS: Skill Evolution triggered and succeeded!")
        logger.info(f"New Skill Description: {skill.description}")
        
        # Verify persistence
        logger.info("\n--- Step 2: Verifying Persistence ---")
        skill_2, reason_2 = await dynamic_skill_manager.get_or_evolve_skill(query)
        logger.info(f"Second Query Result: {skill_2.name} ({skill_2.level})")
        logger.info(f"Reason: {reason_2}")
        
        if skill_2.id == skill.id:
            logger.info("✅ SUCCESS: Retrieved the newly evolved skill from memory!")
        else:
            logger.warning("⚠️ Retrieved a different skill (maybe L2 match?)")
            
    else:
        logger.warning(f"⚠️ Evolution did not happen. Got: {reason}")
        # It might have matched GeneralLearning (L3) but failed to evolve or logic decided not to.

if __name__ == "__main__":
    # Ensure we have API keys if we want real LLM calls, otherwise this might fail or need mocking
    if not settings.OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY found. Evolution might fail if using OpenAI.")
    
    asyncio.run(test_evolution_flow())
