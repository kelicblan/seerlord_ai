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
from server.core.config import settings
from server.core.llm import get_llm

# =============================================================================
# Schema Definitions
# =============================================================================

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

from server.kernel.memory_manager import memory_manager

# =============================================================================
# State Definition
# =============================================================================

class MasterState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    # Context State
    session_id: str
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
    
    # Retrieve Relevant Memories
    memories = []
    if memory_manager.enabled and user_input:
        memories = await memory_manager.retrieve_relevant(user_input, agent_name=agent_name, k=3)
    
    memory_context = ""
    if memories:
        memory_context = "\nRelevant Memories:\n" + "\n".join([f"- {m['content']}" for m in memories]) + "\n"

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

    system_prompt = (
        "You are a Senior Planner for an AI system.\n"
        "Your goal is to break down the user's request into a sequence of executable tasks.\n"
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
    logger.info(f"Dispatching Task {current_task.id}: {current_task.description} -> {current_task.plugin_name}")
    
    # We need to pass the instruction to the plugin.
    # We can inject a SystemMessage or HumanMessage.
    # To avoid polluting the conversation history too much for the user, 
    # we might want to be careful. But plugins rely on 'messages'.
    
    instruction_msg = SystemMessage(content=f"[System Instruction] Execute Task: {current_task.instruction}")
    
    return {
        "target_plugin": current_task.plugin_name,
        "next_instruction": current_task.instruction,
        "messages": [instruction_msg], # Append instruction
        "agent_name": current_task.plugin_name, # Update agent identity to match current plugin
    }

async def chitchat_node(state: MasterState) -> Dict[str, Any]:
    """
    A simple node for general conversation when no plugin is needed.
    """
    llm = get_router_llm()
    # Use context to reply
    response = await llm.ainvoke(state["messages"])
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
        
    # Save Interaction to Memory
    if memory_manager.enabled:
        messages = state.get("messages", [])
        # Find the last human message and the last AI message
        # Note: messages might be mixed. We want the most recent pair.
        last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        
        if last_human and last_ai:
            # Avoid saving duplicates? Qdrant UUID handles ID, but content might be same.
            # We assume each turn is unique enough or we rely on timestamp.
            content_to_save = f"User: {last_human.content}\nAI: {last_ai.content}"
            agent_name = state.get("agent_name", "default_agent")
            session_id = state.get("session_id", "unknown_session")
            
            await memory_manager.save_experience(
                content=content_to_save,
                agent_name=agent_name,
                session_id=session_id
            )

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
        
    # Otherwise, go to approval node (which will interrupt)
    return "human_approval"

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

    workflow = StateGraph(MasterState)
    
    # Add Core Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("dispatcher", dispatcher_node)
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("progress", progress_node)
    workflow.add_node("final_answer", final_answer_node)
    workflow.add_node("human_approval", human_approval_node)
    
    # Entry Point
    workflow.set_entry_point("planner")
    
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
