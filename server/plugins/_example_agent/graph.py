from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from server.core.llm import get_llm
from loguru import logger
from server.memory.tools import memory_node
import uuid
from server.core.database import SessionLocal
from server.models.artifact import AgentArtifact
from server.kernel.skill_integration import skill_injector

from .state import ExampleState
from .schema import ResearchPlan, Reflection
from .tools import search_web, calculate_metrics

def _extract_tokens(response) -> int:
    """
    Extract token usage from LLM response.
    从 LLM 响应中提取 token 使用情况。
    """
    try:
        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage", {})
            return usage.get("total_tokens", 0)
    except Exception:
        pass
    return 0

# =============================================================================
# Node Definitions / 节点定义
# =============================================================================

async def init_node(state: ExampleState):
    """
    Initialize the agent state and extract the user's topic.
    初始化 agent 状态并提取用户的主题。
    
    1. Extract user topic. / 提取用户主题。
    2. Initialize state fields. / 初始化状态字段。
    """
    messages = state["messages"]
    
    # 1. Identify Feedback & Topic / 识别反馈和主题
    external_feedback = []
    topic = ""
    
    # Iterate backwards to find latest feedback and original topic
    # 反向迭代以查找最新的反馈和原始主题
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        content = msg.content
        if isinstance(msg, HumanMessage):
            if content.startswith("[Critic Feedback]"):
                if not external_feedback: # Take the latest one / 取最新的一个
                    external_feedback.append(content)
            else:
                # Found the latest non-feedback human message (the actual topic)
                # 找到最新的非反馈人类消息（实际主题）
                topic = content
                break
                
    # Fallback if no specific topic found (e.g. first run)
    # 如果没有找到特定主题（例如第一次运行），则使用最后一条消息
    if not topic and messages:
        topic = messages[-1].content
    
    # Store topic and initialize fields
    # 存储主题并初始化字段
    return {
        "user_topic": topic,
        "collected_info": [],
        "critique_count": 0,
        "current_task_index": 0,
        "feedback_history": external_feedback,
        "total_tokens": 0
    }

async def local_planner_node(state: ExampleState):
    """
    Generates a research plan (Local Plan).
    生成研究计划（局部计划）。
    
    Utilizes user topic, feedback, memory context, and skills context.
    利用用户主题、反馈、记忆上下文和技能上下文。
    """
    topic = state.get("user_topic", "")
    feedback = state.get("feedback_history", [])
    memory_context = state.get("memory_context", "")
    skills_context = state.get("skills_context", "") # Get skills / 获取技能
    
    llm = get_llm().with_structured_output(ResearchPlan)
    
    prompt = f"Create a research plan for: {topic}.\n"
    if memory_context:
        prompt += f"\n[Memory Context / 记忆上下文]:\n{memory_context}\n"
    
    if skills_context:
        prompt += f"\n[Skills Context / 技能上下文]:\n{skills_context}\n"
        
    if feedback:
        prompt += f"Previous feedback: {feedback[-1]}\nAdjust plan accordingly."
        
    plan = await llm.ainvoke([SystemMessage(content=prompt)])
    
    tokens = _extract_tokens(plan)
    current_tokens = state.get("total_tokens", 0)
    
    return {"local_plan": plan, "current_task_index": 0, "total_tokens": current_tokens + tokens}

async def executor_node(state: ExampleState):
    """
    Executes the current step of the plan.
    执行计划的当前步骤。
    """
    plan = state.get("local_plan")
    idx = state.get("current_task_index", 0)
    
    if not plan or idx >= len(plan.tasks):
        return {} # Should go to reporter / 应该进入报告生成器
        
    task = plan.tasks[idx]
    logger.info(f"Executing task {task.id}: {task.action} - {task.query}")
    
    result = ""
    tokens = 0
    if task.action == "search":
        result = await search_web(task.query)
    elif task.action == "calculate":
        # Example of using a local tool / 使用本地工具的示例
        result = calculate_metrics.invoke(task.query)
    else:
        # Default 'read' or 'summarize' just using LLM / 默认使用 LLM 进行“阅读”或“总结”
        llm = get_llm()
        response = await llm.ainvoke([HumanMessage(content=f"Perform task: {task.action} on {task.query}")])
        result = response.content
        tokens = _extract_tokens(response)
        
    # Append info / 追加信息
    new_info = f"[Task {task.id}] {result}"
    current_info = state.get("collected_info", [])
    current_tokens = state.get("total_tokens", 0)
    
    return {
        "collected_info": current_info + [new_info],
        "current_task_index": idx + 1,
        "total_tokens": current_tokens + tokens
    }

async def reporter_node(state: ExampleState):
    """
    Synthesizes collected info into a final report.
    将收集到的信息综合成最终报告。
    """
    info = "\n".join(state.get("collected_info", []))
    topic = state.get("user_topic")
    
    llm = get_llm()
    prompt = (
        f"Write a comprehensive report on '{topic}'.\n"
        f"Based on the following research:\n{info}\n"
        "Structure it clearly."
    )
    
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    tokens = _extract_tokens(response)
    current_tokens = state.get("total_tokens", 0)
    
    return {"final_report": response.content, "total_tokens": current_tokens + tokens}

async def critic_node(state: ExampleState):
    """
    Self-Reflection loop.
    自我反思循环。
    """
    report = state.get("final_report", "")
    topic = state.get("user_topic")
    
    llm = get_llm().with_structured_output(Reflection)
    
    prompt = (
        f"Critique this report on '{topic}'.\n"
        f"Report:\n{report}\n\n"
        "Check for completeness and clarity."
    )
    
    reflection = await llm.ainvoke([SystemMessage(content=prompt)])
    
    tokens = _extract_tokens(reflection)
    current_tokens = state.get("total_tokens", 0)
    
    if not reflection.is_satisfactory:
        return {
            "feedback_history": state.get("feedback_history", []) + [reflection.feedback],
            "critique_count": state.get("critique_count", 0) + 1,
            "total_tokens": current_tokens + tokens
        }
    
    return {"critique_count": 0, "total_tokens": current_tokens + tokens} # Reset on success (though we end)

async def final_output_node(state: ExampleState):
    """
    Output the final response to the user.
    向用户输出最终响应。
    """
    report = state.get("final_report") or ""
    if report:
        try:
            tenant_id = state.get("tenant_id")
            user_id = state.get("user_id")
            if tenant_id:
                async with SessionLocal() as db:
                    db.add(AgentArtifact(
                        id=str(uuid.uuid4()),
                        tenant_id=str(tenant_id),
                        user_id=str(user_id) if user_id else None,
                        agent_id="_example_agent",
                        type="content",
                        value=str(report),
                        title=f"研究报告：{state.get('user_topic') or ''}",
                        description="示例 agent 生成的研究报告内容",
                        total_tokens=state.get("total_tokens", 0)
                    ))
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to save content artifact: {e}")
    return {"messages": [AIMessage(content=report)]}

# =============================================================================
# Edge Logic / 边逻辑
# =============================================================================

def route_execution(state: ExampleState):
    """
    Route execution based on plan progress.
    根据计划进度路由执行。
    """
    plan = state.get("local_plan")
    idx = state.get("current_task_index", 0)
    
    if plan and idx < len(plan.tasks):
        return "executor"
    return "reporter"

def route_critique(state: ExampleState):
    """
    Route based on critique results.
    根据批评结果进行路由。
    """
    count = state.get("critique_count", 0)
    feedback = state.get("feedback_history", [])
    
    if count > 2: # Max retries / 最大重试次数
        logger.warning("Max critique retries reached.")
        return "final"
        
    if feedback and count > 0:
        # If feedback exists and we just critiqued (and it wasn't cleared), it means failure
        # 如果存在反馈并且我们刚刚进行了批评（并且未被清除），则意味着失败
        # Check if the last node update cleared it? No, critic_node appends feedback.
        # Simple logic: if feedback, go back to planner (replan)
        # 简单逻辑：如果有反馈，回到计划者（重新计划）
        return "planner"
        
    return "final"

# =============================================================================
# Graph Construction / 图构建
# =============================================================================

workflow = StateGraph(ExampleState)

# Add nodes / 添加节点
workflow.add_node("memory_load", memory_node)
workflow.add_node("load_skills", skill_injector.load_skills_context) # Skill loading / 技能加载
workflow.add_node("init", init_node)
workflow.add_node("planner", local_planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reporter", reporter_node)
workflow.add_node("critic", critic_node)
workflow.add_node("final", final_output_node)

# Set entry point / 设置入口点
workflow.set_entry_point("memory_load")

# Add edges / 添加边
workflow.add_edge("memory_load", "load_skills") # Memory -> Skills / 记忆 -> 技能
workflow.add_edge("load_skills", "init")        # Skills -> Init / 技能 -> 初始化

workflow.add_edge("init", "planner")
workflow.add_edge("planner", "executor")

workflow.add_conditional_edges(
    "executor",
    route_execution,
    {
        "executor": "executor", # Loop / 循环
        "reporter": "reporter"  # Done / 完成
    }
)

workflow.add_edge("reporter", "critic")

workflow.add_conditional_edges(
    "critic",
    route_critique,
    {
        "planner": "planner", # Re-plan with feedback / 根据反馈重新计划
        "final": "final"      # Good enough / 足够好
    }
)

workflow.add_edge("final", END)

app = workflow.compile()
