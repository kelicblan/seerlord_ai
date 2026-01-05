from typing import Annotated, List, Dict, Any, Optional, Literal
import uuid
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from loguru import logger

from server.kernel.registry import registry
from server.kernel.skill_registry import skill_registry
from server.core.config import settings
from server.core.llm import get_llm

# =============================================================================
# Schema Definitions
# =============================================================================

class SkillRouterResult(BaseModel):
    """Result of the skill routing decision."""
    skill_name: Optional[str] = Field(description="The name of the skill to execute, or None if no skill matches.")
    arguments: Dict[str, Any] = Field(description="The arguments to pass to the skill.", default_factory=dict)

class Task(BaseModel):
    """A single step in the execution plan."""
    id: int = Field(description="Step number, starting from 1")
    plugin_name: str = Field(description="Name of the plugin to use. Use 'chitchat' for general conversation.")
    instruction: str = Field(description="Specific instruction for this step.")
    description: str = Field(description="Brief description of what this step does.")

class MasterPlan(BaseModel):
    """The global execution plan."""
    tasks: List[Task] = Field(description="List of tasks to execute in order.")
    original_request: str = Field(description="The original user request.")


# =============================================================================
# State Definition
# =============================================================================

class MasterState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    # Context State
    memory_context: str
    session_id: str
    tenant_id: str
    user_id: str
    agent_name: str
    # Planning State
    plan: Optional[MasterPlan]
    current_step_index: int  # 0-based index
    results: Dict[int, str]  # Map task_id to result summary
    # Routing State
    target_plugin: str
    next_instruction: str    # Instruction to pass to the plugin
    # Critique State
    feedback_history: List[str] # List of feedback strings
    retry_count: int            # Number of retries for current task
    # Human Interaction
    user_approval_status: str   # 'pending', 'approved', 'rejected'
    # Skill State
    active_skill: str           # Name of the currently active skill
    skill_args: Dict[str, Any]  # Arguments for the skill
    # Language Preference
    language: str               # Language code (e.g. 'zh-CN', 'en')

# =============================================================================
# Helper Functions
# =============================================================================

# 全局复用 LLM 实例（懒加载）
_router_llm = None

def get_router_llm():
    global _router_llm
    if _router_llm is None:
        _router_llm = get_llm(temperature=0)
    return _router_llm

def sanitize_messages(incoming_messages: List[Any]) -> List[BaseMessage]:
    """
    Ensure all messages are valid LangChain message objects.
    """
    sanitized = []
    for msg in incoming_messages:
        if isinstance(msg, dict):
            msg_type = msg.get("type")
            content = msg.get("content", "")
            msg_id = msg.get("id")
            
            if msg_type == "human":
                sanitized.append(HumanMessage(content=content, id=msg_id))
            elif msg_type == "ai":
                sanitized.append(AIMessage(content=content, id=msg_id))
            elif msg_type == "system":
                sanitized.append(SystemMessage(content=content, id=msg_id))
            elif msg_type == "tool":
                tool_call_id = msg.get("tool_call_id", "unknown")
                sanitized.append(ToolMessage(content=content, tool_call_id=tool_call_id, id=msg_id))
            else:
                sanitized.append(HumanMessage(content=str(content), id=msg_id))
        elif isinstance(msg, BaseMessage):
             # Ensure strict typing if it's a generic BaseMessage
            if type(msg) == BaseMessage:
                if msg.type == "human":
                    sanitized.append(HumanMessage(content=msg.content, id=msg.id, additional_kwargs=msg.additional_kwargs))
                elif msg.type == "ai":
                    sanitized.append(AIMessage(content=msg.content, id=msg.id, additional_kwargs=msg.additional_kwargs))
                elif msg.type == "system":
                    sanitized.append(SystemMessage(content=msg.content, id=msg.id, additional_kwargs=msg.additional_kwargs))
                elif msg.type == "tool":
                    sanitized.append(ToolMessage(content=msg.content, tool_call_id=msg.tool_call_id, id=msg.id, additional_kwargs=msg.additional_kwargs))
                else:
                    sanitized.append(msg)
            else:
                sanitized.append(msg)
        else:
            sanitized.append(HumanMessage(content=str(msg)))
    return sanitized

# =============================================================================
# Nodes
# =============================================================================

async def skill_router_node(state: MasterState) -> Dict[str, Any]:
    """
    Analyzes user input to see if it matches a specific skill.
    """
    # [手动模式覆盖] 如果指定了 target_plugin，跳过技能路由直接进入规划器
    if state.get("target_plugin") and state.get("target_plugin") != "auto":
        return {"active_skill": None}

    messages = sanitize_messages(state.get("messages", []))
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    if not last_user_msg:
        return {"active_skill": None}
    
    user_input = last_user_msg.content
    
    # Check registry
    if not skill_registry.skills:
        skill_registry.scan_and_load()
        
    skills = skill_registry.skills
    if not skills:
        return {"active_skill": None}
        
    import json
    skill_desc_list = []
    for name, s in skills.items():
        # Get schema properties to help LLM understand expected arguments
        schema_props = {}
        if s.args_schema:
            try:
                schema_props = s.args_schema.model_json_schema().get("properties", {})
            except:
                pass
        
        skill_desc_list.append(f"- {name}: {s.description}\n  Expected Arguments: {json.dumps(schema_props)}")
        
    skill_desc = "\n".join(skill_desc_list)
    
    llm = get_router_llm()
    structured_llm = llm.with_structured_output(SkillRouterResult)
    
    system_prompt = (
        "You are an Intent Classifier.\n"
        "Your job is to determine if the user's request matches one of the available skills EXACTLY.\n"
        f"Available Skills:\n{skill_desc}\n"
        "Rules:\n"
        "1. If the request is a direct command for a skill (e.g., 'Calculate 2+2'), return the skill name and arguments.\n"
        "2. ENSURE arguments match the 'Expected Arguments' schema.\n"
        "3. If the request is complex, ambiguous, or requires multi-step reasoning, return None (skill_name=None).\n"
        "4. Only return a skill if you are confident."
    )
    
    try:
        # Use only the last message for routing to keep it focused on immediate intent
        result = await structured_llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_input)])
        if result.skill_name and result.skill_name in skills:
             logger.info(f"Skill Matched: {result.skill_name}")
             return {"active_skill": result.skill_name, "skill_args": result.arguments}
    except Exception as e:
        logger.error(f"Skill routing failed: {e}")
        
    return {"active_skill": None}

async def skill_executor_node(state: MasterState) -> Dict[str, Any]:
    """
    Executes the selected skill.
    """
    skill_name = state.get("active_skill")
    args = state.get("skill_args", {})
    
    if not skill_name or skill_name not in skill_registry.skills:
        return {"messages": [AIMessage(content="Error: Skill not found.")]}
        
    skill = skill_registry.skills[skill_name]
    try:
        logger.info(f"Executing skill {skill_name} with args: {args}")
        output = await skill.ainvoke(args)
        return {"messages": [AIMessage(content=f"Skill Result: {output}")]}
    except Exception as e:
        logger.error(f"Skill execution failed: {e}")
        return {"messages": [AIMessage(content=f"Error executing skill: {e}")]}

class ReflectionResult(BaseModel):
    is_satisfactory: bool = Field(description="Whether the result satisfies the user's request.")
    feedback: str = Field(description="Detailed feedback if not satisfactory, or confirmation if it is.")
    next_action: Literal["continue", "retry", "replan"] = Field(description="Next action to take.")

async def critic_node(state: MasterState) -> Dict[str, Any]:
    """
    Critic Node (Reflector):
    Evaluates the result of the executed plugin task.
    """
    messages = state.get("messages", [])
    plan = state.get("plan")
    idx = state.get("current_step_index", 0)
    
    # If no plan or finished, nothing to critique
    if not plan or idx >= len(plan.tasks):
        return {"next_action": "continue"}

    current_task = plan.tasks[idx]
    
    # Skip critique for chitchat
    if current_task.plugin_name == "chitchat":
        return {"next_action": "continue", "retry_count": 0}

    # Get the last AI message as the result to critique
    last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    if not last_ai_msg:
        # No result produced?
        return {"next_action": "retry", "feedback_history": ["No output produced by plugin."]}

    llm = get_router_llm()
    structured_llm = llm.with_structured_output(ReflectionResult)

    # 获取特定插件的 Critic 指令
    specific_criteria = ""
    if current_task.plugin_name in registry.plugins:
        plugin_instance = registry.plugins[current_task.plugin_name]
        specific_criteria = plugin_instance.get_critique_instructions()
    
    if specific_criteria:
        specific_criteria = f"\n[Specific Plugin Criteria]\n{specific_criteria}\n"

    prompt = (
        f"You are a QA Critic evaluating an AI agent's work.\n"
        f"Task Instruction: {current_task.instruction}\n"
        f"Agent Output: {last_ai_msg.content}\n"
        f"{specific_criteria}\n"
        "Evaluate if the output meets the instruction requirements.\n"
        "If satisfactory, set is_satisfactory=True and next_action='continue'.\n"
        "If minor issues, set next_action='retry' with feedback.\n"
        "If major failure or impossible request, set next_action='replan'.\n"
    )

    try:
        # Check retry count
        retry_count = state.get("retry_count", 0)
        if retry_count >= 3:
            logger.warning(f"Task {current_task.id} failed after 3 retries. Moving on.")
            return {"next_action": "continue", "retry_count": 0, "feedback_history": []}

        result = await structured_llm.ainvoke([SystemMessage(content=prompt)])
        
        logger.info(f"Critic Assessment: {result.next_action} - {result.feedback}")
        
        updates = {
            "next_action": result.next_action,
            "retry_count": retry_count if result.next_action == "continue" else retry_count + 1
        }
        
        if result.next_action != "continue":
            # Add feedback to messages so the plugin sees it on retry
            feedback_msg = HumanMessage(content=f"[Critic Feedback] {result.feedback}")
            updates["messages"] = [feedback_msg]
            
            # Update feedback_history for Planner/UI
            current_history = state.get("feedback_history", [])
            updates["feedback_history"] = current_history + [result.feedback]
            
        return updates

    except Exception as e:
        logger.error(f"Critic failed: {e}")
        return {"next_action": "continue"}

async def planner_node(state: MasterState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Planner Node:
    Analyzes user intent and generates a multi-step execution plan.
    """
    # 1. Ensure Session ID and Agent Name
    session_id = state.get("session_id")
    if not session_id:
        session_id = config.get("configurable", {}).get("thread_id", str(uuid.uuid4()))
    
    agent_name = state.get("agent_name", "default_agent")

    # 2. Check if plan already exists (e.g. from previous turn, though we usually clear it)
    # If we are replanning, we need to respect the feedback
    is_replanning = state.get("next_action") == "replan"
    feedback_history = state.get("feedback_history", [])
    
    messages = sanitize_messages(state.get("messages", []))
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    user_input = last_user_msg.content if last_user_msg else ""
    
    # [手动模式覆盖] 检查是否强制指定了插件
    target_plugin = state.get("target_plugin")
    if target_plugin and target_plugin != "auto" and target_plugin in registry.plugins:
        logger.info(f"手动模式生效: 直接路由至 {target_plugin}")
        return {
             "plan": MasterPlan(
                 tasks=[Task(id=1, plugin_name=target_plugin, instruction=user_input, description="手动选择模式")], 
                 original_request=user_input
             ),
             "current_step_index": 0,
             "results": {},
             "session_id": session_id,
             "agent_name": agent_name
         }

    # Retrieve Relevant Memories (Injected by Middleware)
    memory_context = state.get("memory_context", "")

    plugins = registry.plugins
    
    # Generate plugin descriptions
    if not plugins:
         # No plugins, just chat
         return {
             "plan": MasterPlan(tasks=[Task(id=1, plugin_name="chitchat", instruction="Reply to user", description="Chat")], original_request=user_input),
             "current_step_index": 0,
             "results": {},
             "session_id": session_id,
             "agent_name": agent_name
         }

    plugin_desc = "\n".join([f"- {name}: {p.description}" for name, p in plugins.items()])
    
    llm = get_router_llm()
    structured_llm = llm.with_structured_output(MasterPlan)
    
    replan_context = ""
    if is_replanning and feedback_history:
        replan_context = f"\n\n[ATTENTION] Previous Plan Failed! Feedback: {feedback_history[-1]}\nPlease create a NEW plan to address the failure."

    language = state.get("language", "zh-CN")
    lang_instruction = ""
    if language == "en":
        lang_instruction = "IMPORTANT: Please generate the plan and instructions in English."
    elif language == "zh-TW":
        lang_instruction = "IMPORTANT: Please generate the plan and instructions in Traditional Chinese (繁体中文)."
    else:
        lang_instruction = "IMPORTANT: Please generate the plan and instructions in Simplified Chinese (简体中文)."

    system_prompt = (
        "You are a Senior Planner for an AI system.\n"
        "Your goal is to break down the user's request into a sequence of executable tasks.\n"
        f"{lang_instruction}\n"
        f"{memory_context}\n"
        f"Available Plugins:\n{plugin_desc}\n"
        "- chitchat: Use this for general conversation, greetings, or when no other plugin is suitable.\n\n"
        "Rules:\n"
        "1. If the request is simple (e.g., 'Hi'), create a single 'chitchat' task.\n"
        "2. If the request is complex (e.g., 'Research X and write a report'), break it down.\n"
        "3. Use ONLY available plugins or 'chitchat'.\n"
        "4. Be precise with instructions."
        f"{replan_context}"
    )
    
    try:
        # We only use the last few messages to plan to avoid context overflow
        # But for full context, we might need more.
        plan = await structured_llm.ainvoke([SystemMessage(content=system_prompt)] + messages[-5:])
        logger.info(f"Generated Plan: {plan}")
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        # Fallback plan
        plan = MasterPlan(
            tasks=[Task(id=1, plugin_name="chitchat", instruction="Apologize and say I had trouble planning.", description="Error fallback")],
            original_request=user_input
        )

    return {
        "plan": plan,
        "current_step_index": 0,
        "results": {},
        "messages": messages, # Ensure sanitized
        "session_id": session_id,
        "agent_name": agent_name
    }

async def dispatcher_node(state: MasterState) -> Dict[str, Any]:
    """
    Dispatcher Node:
    Decides the next step based on the plan and current index.
    """
    plan = state.get("plan")
    idx = state.get("current_step_index", 0)
    
    if not plan or idx >= len(plan.tasks):
        return {"target_plugin": "final_answer"}
    
    current_task = plan.tasks[idx]
    # 防御性处理：LLM 生成的 plan 可能包含不存在的插件名，避免进入无限循环
    plugin_name = current_task.plugin_name
    if plugin_name not in registry.plugins and plugin_name != "chitchat":
        logger.warning(f"计划中包含未知插件：{plugin_name}，已降级为 chitchat（task_id={current_task.id}）")
        plugin_name = "chitchat"

    logger.info(f"Dispatching Task {current_task.id}: {current_task.description} -> {plugin_name}")
    
    # We need to pass the instruction to the plugin.
    # We can inject a SystemMessage or HumanMessage.
    # To avoid polluting the conversation history too much for the user, 
    # we might want to be careful. But plugins rely on 'messages'.
    
    language = state.get("language", "zh-CN")
    lang_hint = ""
    if language == "en":
        lang_hint = " (Respond in English)"
    elif language == "zh-TW":
        lang_hint = " (Respond in Traditional Chinese/繁体中文)"
    else:
        lang_hint = " (Respond in Simplified Chinese/简体中文)"

    instruction_msg = SystemMessage(content=f"[System Instruction] Execute Task: {current_task.instruction}{lang_hint}")
    
    return {
        "target_plugin": plugin_name,
        "next_instruction": current_task.instruction,
        "messages": [instruction_msg], # Append instruction
        "agent_name": plugin_name, # Update agent identity to match current plugin
    }

async def chitchat_node(state: MasterState) -> Dict[str, Any]:
    """
    A simple node for general conversation when no plugin is needed.
    """
    llm = get_router_llm()
    
    language = state.get("language", "zh-CN")
    system_msg = ""
    if language == "en":
        system_msg = "respond in English."
    elif language == "zh-TW":
        system_msg = "respond in Traditional Chinese (繁体中文)."
    else:
        system_msg = "respond in Simplified Chinese (简体中文)."

    messages = [SystemMessage(content=system_msg)] + state["messages"]
    
    # Use context to reply
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

async def final_answer_node(state: MasterState) -> Dict[str, Any]:
    """
    Consolidate results and give final answer if needed.
    """
    # Ideally, the last plugin's output is already in messages.
    # We just ensure we are done.
    # We could summarize here if multiple steps were taken.
    
    plan = state.get("plan")
    if plan and len(plan.tasks) > 1:
        # If it was a multi-step task, maybe add a summary message?
        # For now, we assume the last plugin (e.g. 'Write Report') produced the final output.
        pass
        
    # Memory saving is now handled by API Middleware

    return {} # No changes

# =============================================================================
# Edge Logic
# =============================================================================

def route_critique(state: MasterState):
    """
    Routes based on critique result.
    """
    action = state.get("next_action", "continue")
    
    if action == "retry":
        # Retry the same plugin. We need to know which one it was.
        # But dispatcher logic relies on 'target_plugin' being set.
        # It should still be set in state from previous pass.
        return "retry"
    elif action == "replan":
        return "replan"
    else:
        return "continue"

def route_step(state: MasterState):
    """
    Determines where to go from dispatcher.
    """
    target = state.get("target_plugin")
    
    if target == "final_answer":
        return "final_answer"
    
    if target == "chitchat":
        return "chitchat"
        
    if target in registry.plugins:
        return target
        
    # If unknown plugin, skip or error. Go back to dispatcher to try next or finish?
    # Better to fail safely.
    logger.warning(f"Unknown plugin {target}, skipping step.")
    return "dispatcher" # Loop back, which will likely loop forever if we don't increment index.
    # Wait, dispatcher reads current_step_index. If we return to dispatcher without incrementing, loop.
    # We must handle result updates in the plugin edge.
    # But wait, the plugin execution happens in the node.
    # We need a mechanism to increment index AFTER the plugin runs.

# We need a 'post_execution' node or logic.
# LangGraph: Node -> Node.
# We can make the edges from Plugins go to a "progress_node" instead of "dispatcher".

async def progress_node(state: MasterState) -> Dict[str, Any]:
    """
    Increments the step index after a task is completed.
    """
    idx = state.get("current_step_index", 0)
    return {"current_step_index": idx + 1}

async def human_approval_node(state: MasterState) -> Dict[str, Any]:
    """
    Node that waits for human approval.
    This node is set as an interrupt point in the graph compilation.
    When the graph resumes, it implies approval (or we check state).
    """
    logger.info("Resuming from Human Approval...")
    return {"user_approval_status": "approved"}

def route_approval(state: MasterState):
    """
    Decides whether to pause for human approval or proceed.
    """
    plan = state.get("plan")
    if not plan or not plan.tasks:
        return "dispatcher"
        
    # If the only task is chitchat, skip approval
    if len(plan.tasks) == 1 and plan.tasks[0].plugin_name == "chitchat":
        return "dispatcher"
        
    # [Auto-Approval Override]
    # For now, we assume the user wants full automation as per instructions.
    # In a production system, this should be configurable via settings.AUTO_APPROVE
    return "dispatcher"
    
    # Otherwise, go to approval node (which will interrupt)
    # return "human_approval"

def route_skill(state: MasterState):
    """
    Routes based on skill router result.
    """
    if state.get("active_skill"):
        return "skill_executor"
    return "planner"

# =============================================================================
# Graph Builder
# =============================================================================

def build_master_graph(checkpointer=None):
    """
    构建并编译 Master Graph。
    """
    # 确保插件已加载
    if not registry.plugins:
        registry.scan_and_load()
        
    # 确保技能已加载
    if not skill_registry.skills:
        skill_registry.scan_and_load()

    workflow = StateGraph(MasterState)
    
    # Add Core Nodes
    workflow.add_node("skill_router", skill_router_node)
    workflow.add_node("skill_executor", skill_executor_node)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("dispatcher", dispatcher_node)
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("progress", progress_node)
    workflow.add_node("final_answer", final_answer_node)
    workflow.add_node("human_approval", human_approval_node)
    
    # Entry Point
    workflow.set_entry_point("skill_router")
    
    # Skill Router Edges
    workflow.add_conditional_edges(
        "skill_router",
        route_skill,
        {
            "skill_executor": "skill_executor",
            "planner": "planner"
        }
    )
    
    # Skill Executor -> End
    workflow.add_edge("skill_executor", END)
    
    # Planner -> Approval Routing
    workflow.add_conditional_edges(
        "planner",
        route_approval,
        {
            "human_approval": "human_approval",
            "dispatcher": "dispatcher"
        }
    )
    
    # Approval -> Dispatcher
    workflow.add_edge("human_approval", "dispatcher")
    
    # Dispatcher -> (Plugin / Chitchat / Final)
    workflow.add_conditional_edges(
        "dispatcher",
        route_step,
        {
            "final_answer": "final_answer",
            "chitchat": "chitchat",
            **{name: name for name in registry.plugins.keys()} # Map plugin names to nodes
        }
    )
    
    # Plugins -> Critic (was Progress)
    for name, plugin in registry.plugins.items():
        logger.info(f"Mounting plugin to graph: {name}")
        workflow.add_node(name, plugin.get_graph())
        workflow.add_edge(name, "critic")
        
    # Chitchat -> Progress (Skip critic for chitchat usually, or route to critic but critic skips it)
    workflow.add_edge("chitchat", "progress")
    
    # Critic -> (Progress / Retry(Dispatcher) / Replan(Planner))
    workflow.add_conditional_edges(
        "critic",
        route_critique,
        {
            "continue": "progress",
            "retry": "dispatcher", # Go back to dispatcher which will re-invoke the SAME target_plugin
            "replan": "planner"
        }
    )
    
    # Progress -> Dispatcher (Loop)
    workflow.add_edge("progress", "dispatcher")
    
    # Final Answer -> END
    workflow.add_edge("final_answer", END)

    # Set interrupt point
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])
