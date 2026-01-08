from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from loguru import logger

from server.kernel.skill_service import skill_service
from server.kernel.hierarchical_skills import HierarchicalSkill, GLOBAL_SKILL_TENANT_ID

class SkillInjector:
    """
    Universal component to inject skills into Agent workflows.
    Supports Context Mode (injecting prompts) and Tool Mode (binding tools).
    """

    @staticmethod
    async def load_skills_context(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph Node: Retrieves skills and injects them as a SystemMessage.
        
        Usage in Graph:
        workflow.add_node("load_skills", SkillInjector.load_skills_context)
        workflow.add_edge("load_skills", "agent_node")
        """
        messages = state.get("messages", [])
        
        # 1. Extract Query
        query = "General Task"
        # Try to find the last human message
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                query = m.content
                break
        
        # 2. Extract Context
        # Force GLOBAL tenant for skill loading
        tenant_id = GLOBAL_SKILL_TENANT_ID
        user_id = state.get("user_id")
        agent_description = state.get("agent_description", "")
        
        # 3. Retrieve Skills (with Evolution)
        skills = await skill_service.retrieve_skills_for_query(
            query, 
            tenant_id=tenant_id, 
            user_id=user_id, 
            agent_description=agent_description
        )
        
        if not skills:
            return {}

        # 4. Format Context
        skill_prompts = []
        used_ids = []
        for s in skills:
            # Handle both object and dict (just in case)
            if isinstance(s, dict):
                # Fallback if somehow we got dicts
                name = s.get('name')
                content = s.get('content', {})
                prompt = content.get('prompt_template', '') if isinstance(content, dict) else str(content)
            else:
                name = s.name
                prompt = s.content.prompt_template
                used_ids.append(s.id)

            skill_prompts.append(f"--- EXPERT SKILL: {name} ---\n{prompt}")
            
        context_str = "\n\n".join(skill_prompts)
        
        logger.info(f"Injecting {len(skills)} skills into context for query: {query[:20]}...")

        # 5. Create System Message
        # We prepend a SystemMessage instructing the LLM to use these skills.
        skill_msg = SystemMessage(content=f"""
[SYSTEM: DYNAMIC SKILLS ACTIVE]
The following expert skills have been retrieved to assist with the current task. 
You MUST adopt the perspectives, methodologies, and knowledge provided below:

{context_str}

[END SKILLS]
""")
        
        # 6. Return State Update
        # We append to messages. LangGraph will merge this list.
        # Ideally, this should come BEFORE the latest human message in the final prompt,
        # but appending it here usually works if the model handles a list of messages.
        return {
            "messages": [skill_msg], 
            "skills_context": context_str,
            "used_skill_ids": used_ids
        }

    @staticmethod
    async def get_skill_tools(query: str, tenant_id: str, user_id: str) -> List[StructuredTool]:
        """
        Helper to get skills as Tools (for Tool Mode agents).
        Currently returns placeholders, as converting text skills to executable code dynamically is complex.
        In the future, this can map 'code_logic' from skills to LangChain Tools.
        """
        # Placeholder for Tool Mode
        return []

skill_injector = SkillInjector()
