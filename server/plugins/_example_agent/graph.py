from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from server.core.llm import get_llm
from server.kernel.memory_manager import memory_manager
from loguru import logger

from .state import ExampleState
from .schema import ResearchPlan, Reflection
from .tools import search_web, calculate_metrics

# =============================================================================
# Node Definitions
# =============================================================================

async def init_node(state: ExampleState):
    """
    1. Extract user topic.
    2. Retrieve relevant memory.
    """
    messages = state["messages"]
    
    # 1. Identify Feedback & Topic
    external_feedback = []
    topic = ""
    
    # Iterate backwards to find latest feedback and original topic
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        content = msg.content
        if isinstance(msg, HumanMessage):
            if content.startswith("[Critic Feedback]"):
                if not external_feedback: # Take the latest one
                    external_feedback.append(content)
            else:
                # Found the latest non-feedback human message (the actual topic)
                topic = content
                break
                
    # Fallback if no specific topic found (e.g. first run)
    if not topic and messages:
        topic = messages[-1].content
    
    # Memory Retrieval (Demonstration)
    memories = []
    if memory_manager.enabled:
        tenant_id = state.get("tenant_id", "default_tenant")
        user_id = state.get("user_id")
        memories = await memory_manager.retrieve_relevant(
            query=topic, 
            tenant_id=tenant_id, 
            user_id=user_id,
            k=2
        )
    
    memory_context = ""
    if memories:
        memory_context = "\n[Memory Context]: " + "; ".join([m["content"] for m in memories])
    
    # Store topic and initialize fields
    return {
        "user_topic": topic + memory_context,
        "collected_info": [],
        "critique_count": 0,
        "current_task_index": 0,
        "feedback_history": external_feedback
    }

async def local_planner_node(state: ExampleState):
    """
    Generates a research plan (Local Plan).
    """
    topic = state.get("user_topic", "")
    feedback = state.get("feedback_history", [])
    
    llm = get_llm().with_structured_output(ResearchPlan)
    
    prompt = f"Create a research plan for: {topic}.\n"
    if feedback:
        prompt += f"Previous feedback: {feedback[-1]}\nAdjust plan accordingly."
        
    plan = await llm.ainvoke([SystemMessage(content=prompt)])
    
    return {"local_plan": plan, "current_task_index": 0}

async def executor_node(state: ExampleState):
    """
    Executes the current step of the plan.
    """
    plan = state.get("local_plan")
    idx = state.get("current_task_index", 0)
    
    if not plan or idx >= len(plan.tasks):
        return {} # Should go to reporter
        
    task = plan.tasks[idx]
    logger.info(f"Executing task {task.id}: {task.action} - {task.query}")
    
    result = ""
    if task.action == "search":
        result = await search_web(task.query)
    elif task.action == "calculate":
        # Example of using a local tool
        result = calculate_metrics.invoke(task.query)
    else:
        # Default 'read' or 'summarize' just using LLM
        llm = get_llm()
        result = await llm.ainvoke([HumanMessage(content=f"Perform task: {task.action} on {task.query}")])
        result = result.content
        
    # Append info
    new_info = f"[Task {task.id}] {result}"
    current_info = state.get("collected_info", [])
    
    return {
        "collected_info": current_info + [new_info],
        "current_task_index": idx + 1
    }

async def reporter_node(state: ExampleState):
    """
    Synthesizes collected info into a final report.
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
    
    return {"final_report": response.content}

async def critic_node(state: ExampleState):
    """
    Self-Reflection loop.
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
    
    if not reflection.is_satisfactory:
        return {
            "feedback_history": state.get("feedback_history", []) + [reflection.feedback],
            "critique_count": state.get("critique_count", 0) + 1
        }
    
    return {"critique_count": 0} # Reset on success (though we end)

async def final_output_node(state: ExampleState):
    """
    Output the final response to the user.
    """
    report = state.get("final_report")
    # Wrap in AIMessage for the Master Graph
    return {"messages": [AIMessage(content=report)]}

# =============================================================================
# Edge Logic
# =============================================================================

def route_execution(state: ExampleState):
    plan = state.get("local_plan")
    idx = state.get("current_task_index", 0)
    
    if plan and idx < len(plan.tasks):
        return "executor"
    return "reporter"

def route_critique(state: ExampleState):
    count = state.get("critique_count", 0)
    feedback = state.get("feedback_history", [])
    
    if count > 2: # Max retries
        logger.warning("Max critique retries reached.")
        return "final"
        
    if feedback and count > 0:
        # If feedback exists and we just critiqued (and it wasn't cleared), it means failure
        # Check if the last node update cleared it? No, critic_node appends feedback.
        # So if we are here, check if we need to replan or rewrite.
        # Simple logic: if feedback, go back to planner (replan)
        return "planner"
        
    return "final"

# =============================================================================
# Graph Construction
# =============================================================================

workflow = StateGraph(ExampleState)

workflow.add_node("init", init_node)
workflow.add_node("planner", local_planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reporter", reporter_node)
workflow.add_node("critic", critic_node)
workflow.add_node("final", final_output_node)

workflow.set_entry_point("init")

workflow.add_edge("init", "planner")
workflow.add_edge("planner", "executor")

workflow.add_conditional_edges(
    "executor",
    route_execution,
    {
        "executor": "executor", # Loop
        "reporter": "reporter"  # Done
    }
)

workflow.add_edge("reporter", "critic")

workflow.add_conditional_edges(
    "critic",
    route_critique,
    {
        "planner": "planner", # Re-plan with feedback
        "final": "final"      # Good enough
    }
)

workflow.add_edge("final", END)

graph = workflow.compile()
