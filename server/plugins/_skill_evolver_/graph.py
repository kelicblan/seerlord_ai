from typing import Dict, List, Any, cast
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from server.core.llm import get_llm
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.plugins._skill_evolver_.state import EvolverState
from server.memory.tools import memory_node

# --- Node Implementations ---

async def analyze_gap(state: EvolverState) -> Dict[str, Any]:
    """Analyze the conversation history to identify skill gaps."""
    llm = get_llm(temperature=0.3)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Skill Architect. Analyze the conversation to identify why the current skills were insufficient."),
        ("human", """
        Task: {task}
        
        Conversation History:
        {history}
        
        Related Skills Available:
        {skills}
        
        Output your analysis of the missing knowledge or capability.
        """)
    ])
    
    chain = prompt | llm
    
    # Format history and skills for prompt
    history_text = "\n".join([f"{m.type}: {m.content}" for m in state["conversation_history"]])
    skills_text = "\n".join([f"- {s.name} ({s.level}): {s.description}" for s in state["related_skills"]])
    
    response = await chain.ainvoke({
        "task": state["task"],
        "history": history_text,
        "skills": skills_text
    })
    
    return {"reasoning_log": [response.content]}

async def draft_skill(state: EvolverState) -> Dict[str, Any]:
    """Draft a new HierarchicalSkill based on analysis."""
    llm = get_llm(temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Skill Architect. Create a structured Skill definition.
        Return ONLY a JSON object compatible with the HierarchicalSkill schema.
        
        Schema Rules:
        - name: PascalCase (e.g., CalculateTax)
        - level: "specific" (L1) or "domain" (L2)
        - description: Concise summary for semantic search.
        - content: 
            - prompt_template: The system prompt for the agent performing this skill.
            - knowledge_base: List of key facts/rules.
        """),
        ("human", """
        Analysis:
        {analysis}
        
        Draft the skill now.
        """)
    ])
    
    chain = prompt | llm
    
    analysis = state["reasoning_log"][-1]
    response = await chain.ainvoke({"analysis": analysis})
    
    # Parse JSON (simplified for now)
    import json
    import re
    from server.kernel.hierarchical_manager import HierarchicalSkillManager
    
    content = response.content
    # Extract JSON block
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            data = json.loads(json_str)
            # Ensure minimal fields
            if "content" in data and isinstance(data["content"], dict):
                # Basic validation passed, construct object
                # Note: ID and stats are auto-generated
                skill = HierarchicalSkill(
                    name=data.get("name", "NewSkill"),
                    description=data.get("description", ""),
                    level=data.get("level", "specific"),
                    content=SkillContent(**data["content"]),
                    parent_id=data.get("parent_id")
                )
                
                # Note: We do NOT save here anymore. 
                # The DynamicSkillManager handles persistence to SQL/Qdrant with proper context (tenant/user).
                
                return {"proposed_skill": skill, "evolution_report": f"Skill '{skill.name}' created and saved successfully."}
        except Exception as e:
            return {"evolution_report": f"Failed to parse or save skill JSON: {e}"}
            
    return {"evolution_report": "No valid JSON found in response."}

# --- Graph Definition ---

workflow = StateGraph(EvolverState)

workflow.add_node("memory_load", memory_node)
workflow.add_node("analyze_gap", analyze_gap)
workflow.add_node("draft_skill", draft_skill)

workflow.set_entry_point("memory_load")
workflow.add_edge("memory_load", "analyze_gap")
workflow.add_edge("analyze_gap", "draft_skill")
workflow.add_edge("draft_skill", END)

app = workflow.compile()
