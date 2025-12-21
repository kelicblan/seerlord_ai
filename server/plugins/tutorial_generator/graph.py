from typing import Annotated, List, Dict, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks.manager import adispatch_custom_event
from pydantic import BaseModel, Field
from server.core.config import settings
from server.core.llm import get_llm
from server.kernel.dynamic_skill_manager import dynamic_skill_manager
from server.kernel.skill_service import skill_service
from server.kernel.feedback_service import skill_feedback_service
from .schema import TutorialSchema
from .state import TutorialState

# Define Structured Output for Critique
class CritiqueResult(BaseModel):
    score: int = Field(description="Score from 1 to 10. 10 is perfect.")
    critique: str = Field(description="Detailed critique of the tutorial outline.")
    suggestions: str = Field(description="Specific suggestions for improvement.")

def analyze_intent(state: TutorialState):
    """
    分析用户意图节点。
    """
    return {"messages": [SystemMessage(content="Analyzing user request for tutorial generation...")]}

async def generate_content_with_skills(state: TutorialState):
    """
    使用 Skill System (RAG) 检索技能并注入 Prompt 生成内容。
    """
    from loguru import logger
    
    messages = state.get("messages", [])
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_user_msg.content if last_user_msg else "Generate a learning plan"
    
    logger.info(f"Tutorial Agent processing query: {query}")
    
    # 1. 技能检索 (Skill Retrieval)
    # 基于用户查询，召回相关的 L3 -> L2 -> L1 技能链
    retrieved_skills = skill_service.retrieve_skills_for_query(query, category='tutorial_agent')
    
    skill_prompts = []
    skill_names = []
    used_ids = []
    
    for skill in retrieved_skills:
        skill_names.append(f"{skill.name} (L{skill.level})")
        used_ids.append(skill.id)
        # 格式化技能注入
        skill_prompts.append(f"--- SKILL: {skill.name} (L{skill.level}) ---\n{skill.content}")
    
    skills_context = "\n\n".join(skill_prompts)
    logger.info(f"Skills Injected: {', '.join(skill_names)}")
    
    # Emit Skill Usage Event for Frontend
    await adispatch_custom_event(
        "skill_usage",
        {
            "used_skills": [
                {"id": s.id, "name": s.name, "level": s.level} 
                for s in retrieved_skills
            ]
        }
    )

    # --- SIMULATE EVOLUTION (Demo Logic) ---
    # If user explicitly asks for optimization or if random chance (in real life: based on feedback)
    if "optimize" in query.lower() or "evolve" in query.lower():
        # Simulate evolving the first L1 skill found
        target_skill = next((s for s in retrieved_skills if s.level == 1), None)
        if target_skill:
            logger.info(f"Triggering evolution for skill: {target_skill.name}")
            new_content = target_skill.content + "\n\n[Optimization]: Added concrete examples based on recent feedback."
            skill_service.log_evolution(
                skill_id=target_skill.id,
                agent_id="tutorial_generator",
                change_desc="User requested optimization during execution",
                new_content=new_content
            )
            # Emit Evolution Event
            await adispatch_custom_event(
                "skill_evolution",
                {
                    "skill_id": target_skill.id,
                    "skill_name": target_skill.name,
                    "change": "Optimization triggered by user request"
                }
            )

    # 2. 构造最终 Prompt
    # 将“固化的智慧食谱”注入给 LLM
    system_prompt = f"""You are an expert Educational Content Generator.
    
    You have been trained with the following SPECIFIC SKILLS. You MUST follow them strictly to ensure high-quality teaching.
    
    === ACTIVE SKILLS (High Priority) ===
    {skills_context}
    =====================================
    
    Based on the above skills, please generate the tutorial content for the user's request.
    If no specific skill matches the topic, rely on the 'Meta-Learning' (L3) skill for general guidance.
    """
    
    # 3. 执行 (Streaming Mode)
    llm = get_llm(temperature=0.7)
    
    execution_messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
    
    # Use astream to ensure 'on_chat_model_stream' events are emitted for the frontend
    # ainvoke with ChatOpenAI(Ollama) might not stream chunks correctly
    # But astream seems to be failing to propagate to frontend in this specific agent context
    # Switching to ainvoke which is known to work in other agents (like news_reporter)
    
    logger.info("Generating content with ainvoke...")
    response = await llm.ainvoke(execution_messages)
    response_content = response.content
    
    # response_content = ""
    # logger.info("Starting LLM stream...")
    # async for chunk in llm.astream(execution_messages):
    #     content = chunk.content
    #     # logger.debug(f"Chunk received: {content[:20]}...")
    #     response_content += content
    
    # logger.info(f"LLM stream finished. Total length: {len(response_content)}")
    
    final_message = AIMessage(content=response_content)
    
    return {
        "detailed_content": response_content,
        "messages": [final_message],
        "used_skill_ids": used_ids,
        # Add fallback results key for frontend to pick up if streaming fails
        "results": {
            "generate_content": response_content
        }
    }

async def collect_feedback(state: TutorialState):
    """
    (Optional Node) 模拟收集用户反馈并触发进化
    在实际生产中，这通常是异步的（用户点赞/点踩后触发接口），但为了演示，我们在这里模拟一个负反馈流程。
    """
    # 假设我们在这里模拟用户反馈
    # 实际场景下，这一步是 API 调用
    # 这里我们只记录日志，或者如果有负面评价，调用 skill_feedback_service
    pass

# --- Graph Definition ---

tutorial_graph = StateGraph(TutorialState)

tutorial_graph.add_node("analyze_intent", analyze_intent)
# 直接连接到新的基于技能的内容生成器
tutorial_graph.add_node("generate_content", generate_content_with_skills)
tutorial_graph.add_node("collect_feedback", collect_feedback) # Placeholder

tutorial_graph.set_entry_point("analyze_intent")
tutorial_graph.add_edge("analyze_intent", "generate_content")
tutorial_graph.add_edge("generate_content", "collect_feedback")
tutorial_graph.add_edge("collect_feedback", END)

tutorial_graph = tutorial_graph.compile()
