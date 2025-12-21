from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from server.core.llm import get_llm
from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.plugins._voyager_agent_.state import VoyagerState

# --- Nodes ---

async def retrieve_skill(state: VoyagerState) -> Dict[str, Any]:
    """
    Determine user intent and retrieve/evolve the best skill.
    """
    last_message = state["messages"][-1]
    query = last_message.content
    
    # Use the Dynamic Manager which handles Fallback -> Evolution
    skill, reason = await dynamic_skill_manager.get_or_evolve_skill(
        query=query, 
        tenant_id=state.get("tenant_id", "default_tenant"),
        user_id=state.get("user_id"),
        agent_name="voyager_agent",
        conversation_history=state["messages"]
    )
    
    return {
        "current_skill": skill,
        "skill_match_reason": reason
    }

async def execute_task(state: VoyagerState) -> Dict[str, Any]:
    """
    Execute the task using the retrieved skill's prompt/logic.
    """
    skill = state["current_skill"]
    llm = get_llm(temperature=0.7)
    
    # Construct System Prompt based on Skill Content
    system_prompt = f"""You are an AI Agent equipped with the skill: '{skill.name}'.
    
    Skill Description: {skill.description}
    
    Skill Instructions:
    {skill.content.prompt_template}
    
    Knowledge Base:
    {chr(10).join(['- '+k for k in skill.content.knowledge_base])}
    
    Please execute the user's request using this skill effectively.
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    response = await llm.ainvoke(messages)
    
    return {
        "messages": [response],
        "execution_result": response.content
    }

# --- Graph ---

workflow = StateGraph(VoyagerState)

workflow.add_node("retrieve_skill", retrieve_skill)
workflow.add_node("execute_task", execute_task)

workflow.set_entry_point("retrieve_skill")
workflow.add_edge("retrieve_skill", "execute_task")
workflow.add_edge("execute_task", END)

app = workflow.compile()
