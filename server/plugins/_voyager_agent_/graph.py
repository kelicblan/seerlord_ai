from typing import Dict, Any
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from server.core.llm import get_llm
from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.plugins._voyager_agent_.state import VoyagerState
from server.memory.tools import memory_node

# --- Nodes ---

async def retrieve_skill(state: VoyagerState) -> Dict[str, Any]:
    """
    Determine user intent and retrieve/evolve the best skill.
    """
    # Get the last user message
    messages = state["messages"]
    # Filter for the last human message if possible, or just take the last message
    last_message = messages[-1]
    query = last_message.content
    
    # Use the Dynamic Manager which handles Fallback -> Evolution
    skill, reason = await dynamic_skill_manager.get_or_evolve_skill(
        query=query, 
        tenant_id=state.get("tenant_id", "default_tenant"),
        user_id=state.get("user_id"),
        agent_name="voyager_agent",
        conversation_history=messages
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
    memory_context = state.get("memory_context", "")
    llm = get_llm(temperature=0.7)
    
    # Construct System Prompt based on Skill Content
    system_prompt = f"""You are an AI Agent equipped with the skill: '{skill.name}'.
    
    {memory_context}
    
    Skill Description: {skill.description}
    
    Skill Instructions:
    {skill.content.prompt_template}
    
    Knowledge Base:
    {chr(10).join(['- '+k for k in skill.content.knowledge_base])}
    
    Please execute the user's request using this skill effectively.
    """
    
    # Ensure we don't duplicate system messages if they persist in state (LangGraph appends usually)
    # But here we construct a fresh prompt for the execution.
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    response = await llm.ainvoke(messages)
    
    return {
        "messages": [response],
        "execution_result": response.content
    }

async def critic_node(state: VoyagerState) -> Dict[str, Any]:
    """
    Evaluate execution result and decide if skill needs refinement.
    """
    llm = get_llm(temperature=0.1)
    
    # Extract original task (last human message)
    task = "Unknown"
    for msg in reversed(state["messages"][:-1]): # Skip the last AIMessage we just added
        if isinstance(msg, HumanMessage):
            task = msg.content
            break
            
    prompt = f"""Evaluate the following task execution by an AI Agent.
    
    Task: {task}
    Skill Used: {state['current_skill'].name}
    Result: {state['execution_result']}
    
    Did the skill execute perfectly? 
    - If the result is correct and high quality, return false.
    - If there are errors, hallucinations, format issues, or it failed to follow instructions, return true.
    
    Return JSON ONLY:
    {{
        "needs_refinement": boolean,
        "reason": "concise explanation of what went wrong or could be improved"
    }}
    """
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "needs_refinement": data.get("needs_refinement", False),
                "critic_feedback": data.get("reason", "")
            }
    except Exception as e:
        print(f"Critic failed: {e}")
        
    return {"needs_refinement": False, "critic_feedback": ""}

async def refine_skill_node(state: VoyagerState) -> Dict[str, Any]:
    """Call Dynamic Manager to refine the skill."""
    skill = state["current_skill"]
    feedback = state["critic_feedback"]
    
    # Only refine if it's not a system/meta skill (optional check, but good for safety)
    # The manager handles most logic, but we can skip here if needed.
    
    await dynamic_skill_manager.refine_existing_skill(
        skill=skill,
        feedback=feedback,
        tenant_id=state.get("tenant_id", "default_tenant"),
        user_id=state.get("user_id")
    )
    
    return {}

# --- Graph ---

def route_critic(state: VoyagerState) -> str:
    if state.get("needs_refinement"):
        return "refine_skill_node"
    return END

workflow = StateGraph(VoyagerState)

workflow.add_node("memory_load", memory_node)
workflow.add_node("retrieve_skill", retrieve_skill)
workflow.add_node("execute_task", execute_task)
workflow.add_node("critic_node", critic_node)
workflow.add_node("refine_skill_node", refine_skill_node)

workflow.set_entry_point("memory_load")

workflow.add_edge("memory_load", "retrieve_skill")
workflow.add_edge("retrieve_skill", "execute_task")
workflow.add_edge("execute_task", "critic_node")

workflow.add_conditional_edges(
    "critic_node",
    route_critic,
    {
        "refine_skill_node": "refine_skill_node",
        END: END
    }
)

workflow.add_edge("refine_skill_node", END)

app = workflow.compile()
