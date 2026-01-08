from typing import Dict, List, Any, cast
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from server.core.llm import get_llm
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.plugins._skill_evolver_.state import EvolverState
from server.memory.tools import memory_node

import json
import re

# --- Node Implementations ---

async def analyze_gap(state: EvolverState) -> Dict[str, Any]:
    """Analyze the conversation history to identify skill gaps."""
    llm = get_llm(temperature=0.3)
    
    agent_description = state.get("agent_description", "Generic Agent")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Skill Architect. Analyze the conversation to identify why the current skills were insufficient."),
        ("human", """
        You are designing a skill for an Agent described as: 
        "{agent_desc}"
        
        The user asked: 
        "{task}"
        
        Conversation History:
        {history}
        
        Related Skills Available:
        {skills}
        
        Analyze what specific cognitive capability or procedural knowledge is missing for THIS SPECIFIC AGENT to answer the user's request.
        Ignore trivial output formats (like "send email") unless it's the core function. Focus on the core reasoning or data processing task.
        """)
    ])
    
    chain = prompt | llm
    
    # Format history and skills for prompt
    history_text = "\n".join([f"{m.type}: {m.content}" for m in state["conversation_history"]])
    skills_text = "\n".join([f"- {s.name} ({s.level}): {s.description}" for s in state["related_skills"]])
    
    response = await chain.ainvoke({
        "agent_desc": agent_description,
        "task": state["task"],
        "history": history_text,
        "skills": skills_text
    })
    
    return {"reasoning_log": [response.content]}

async def draft_skill(state: EvolverState) -> Dict[str, Any]:
    """Draft a new HierarchicalSkill based on analysis."""
    llm = get_llm(temperature=0.1)
    
    agent_description = state.get("agent_description", "Generic Agent")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Skill Architect. Create a structured Skill definition.
        Return ONLY a JSON object compatible with the HierarchicalSkill schema.
        
        Schema Rules:
        - name: PascalCase (e.g., AnalyzeTechTrends)
        - level: "specific" (L1) or "domain" (L2)
        - description: Concise summary for semantic search.
        - content: 
            - prompt_template: The system prompt for the agent performing this skill.
            - knowledge_base: List of key facts/rules.
            
        CRITICAL GUIDELINES:
        1. The 'prompt_template' MUST be designed for an Agent with this description: "{agent_desc}".
        2. It should guide the Agent to solve the user's specific request: "{task}".
        3. Do NOT include generic instructions like "You are a helpful assistant". Use the specific persona.
        4. Focus on HOW to think, analyze, or process data, not just on formatting the output.
        """),
        ("human", """
        Analysis:
        {analysis}
        
        Draft the skill now.
        """)
    ])
    
    chain = prompt | llm
    
    analysis = state["reasoning_log"][-1]
    response = await chain.ainvoke({
        "agent_desc": agent_description,
        "task": state["task"],
        "analysis": analysis
    })
    
    return _parse_skill_response(response.content, parent_id=None)

async def refine_skill(state: EvolverState) -> Dict[str, Any]:
    """Refine an existing skill based on feedback."""
    llm = get_llm(temperature=0.1)
    
    skill = state["skill_to_refine"]
    if not skill:
        return {"evolution_report": "Error: No skill provided for refinement."}
        
    feedback = state.get("execution_feedback", "No feedback provided.")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Skill Architect. Your task is to OPTIMIZE an existing skill based on execution feedback.
        
        Return ONLY a JSON object compatible with the HierarchicalSkill schema (preserving the same structure).
        Do NOT include any markdown formatting (like ```json), explanations, or chatter. Just the raw JSON string.
        
        Example JSON Structure:
        {{
            "name": "SkillName",
            "description": "...",
            "level": "specific",
            "content": {{
                "prompt_template": "...",
                "knowledge_base": ["..."]
            }}
        }}
        
        Focus on improving:
        1. The 'prompt_template' to be more precise or handle edge cases.
        2. The 'knowledge_base' to add missing facts found in feedback.
        
        Do NOT change the skill name unless necessary.
        """),
        ("human", """
        Original Skill:
        Name: {name}
        Description: {description}
        Prompt: {prompt_template}
        Knowledge: {knowledge}
        
        Execution Feedback:
        {feedback}
        
        Refine the skill now. Return the full JSON.
        """)
    ])
    
    chain = prompt | llm
    
    response = await chain.ainvoke({
        "name": skill.name,
        "description": skill.description,
        "prompt_template": skill.content.prompt_template,
        "knowledge": "\n".join(skill.content.knowledge_base),
        "feedback": feedback
    })
    
    # We pass the original skill ID as parent_id to track lineage (optional, or handle in manager)
    # Actually, for refinement, we might want to keep the same ID or let the manager handle versioning.
    # Here we just return the new definition. The manager handles the DB update.
    return _parse_skill_response(response.content, parent_id=skill.id)

def _parse_skill_response(content: str, parent_id: str = None) -> Dict[str, Any]:
    """Helper to parse JSON skill definition from LLM response."""
    # Clean up markdown code blocks if present
    content = content.replace("```json", "").replace("```", "").strip()
    
    # Extract JSON block
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            data = json.loads(json_str)
            # Ensure minimal fields
            if "content" in data and isinstance(data["content"], dict):
                # Basic validation passed, construct object
                skill = HierarchicalSkill(
                    name=data.get("name", "NewSkill"),
                    description=data.get("description", ""),
                    level=data.get("level", "specific"),
                    content=SkillContent(**data["content"]),
                    parent_id=parent_id 
                )
                
                return {"proposed_skill": skill, "evolution_report": f"Skill '{skill.name}' processed successfully."}
        except Exception as e:
            return {"evolution_report": f"Failed to parse or save skill JSON: {e}"}
            
    return {"evolution_report": "No valid JSON found in response."}

# --- Graph Definition ---

def route_evolution(state: EvolverState) -> str:
    """Decide whether to draft new skill or refine existing one."""
    if state.get("skill_to_refine"):
        return "refine_skill"
    return "analyze_gap"

workflow = StateGraph(EvolverState)

workflow.add_node("memory_load", memory_node)
workflow.add_node("analyze_gap", analyze_gap)
workflow.add_node("draft_skill", draft_skill)
workflow.add_node("refine_skill", refine_skill)

workflow.set_entry_point("memory_load")

# Conditional routing
workflow.add_conditional_edges(
    "memory_load",
    route_evolution,
    {
        "analyze_gap": "analyze_gap",
        "refine_skill": "refine_skill"
    }
)

workflow.add_edge("analyze_gap", "draft_skill")
workflow.add_edge("draft_skill", END)
workflow.add_edge("refine_skill", END)

app = workflow.compile()
