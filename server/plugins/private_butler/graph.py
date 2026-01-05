from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from server.core.llm import get_llm
from server.plugins.private_butler.state import ButlerState
from server.plugins.private_butler.tools import memory_write, memory_read
from server.kernel.skill_integration import skill_injector
from loguru import logger

# --- Models ---

class RouterOutput(BaseModel):
    intent: Literal["MEMORY_READ", "MEMORY_WRITE", "TASK", "CHITCHAT", "PROACTIVE"] = Field(
        ..., description="The classified intent of the user."
    )

# --- Nodes ---

async def supervisor_node(state: ButlerState):
    """
    Classifies the user's intent.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    # Check for Proactive Trigger (System Signal)
    if isinstance(last_msg, HumanMessage) and "EXECUTE_DAILY_BRIEFING" in last_msg.content:
        logger.info("Proactive trigger detected.")
        return {"user_intent": "PROACTIVE"}
        
    # LLM Classification
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(RouterOutput)
    
    system_prompt = (
        "You are the Supervisor of a Private Butler Agent. "
        "Classify the user's input into one of the following categories:\n\n"
        "1. MEMORY_WRITE (Collection): User provides information about themselves, their life, work, or preferences.\n"
        "   - Examples: 'My birthday is Dec 30', 'I like apples', 'I am a software engineer'.\n\n"
        "2. MEMORY_READ (Consultation): User asks a question that might involve personal context OR general knowledge mixed with personal context.\n"
        "   - CRITICAL: If the user asks 'What is X?' (e.g., 'What is Dec 30?'), classify as MEMORY_READ so we can check if X has personal significance (like a birthday) before answering with general knowledge.\n"
        "   - Examples: 'When is my birthday?', 'What is Dec 30?', 'Where do I live?'.\n\n"
        "3. TASK: User asks to perform an external action (email, calendar, search).\n\n"
        "4. CHITCHAT: Purely casual conversation with NO potential personal entity reference.\n"
        "   - Only select this if you are sure the query (e.g., 'Hi', 'How are you') does not need memory lookup.\n\n"
        "5. PROACTIVE: (Internal use only).\n"
    )
    
    try:
        result = await structured_llm.ainvoke([SystemMessage(content=system_prompt), last_msg])
        intent = result.intent
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        intent = "CHITCHAT"
        
    logger.info(f"Supervisor routed to: {intent}")
    return {"user_intent": intent}

async def memory_agent_node(state: ButlerState):
    """
    Handles memory operations (Read/Write).
    """
    llm = get_llm(temperature=0)
    user_id = state.get("user_id")
    if not user_id:
        # Fallback or error
        user_id = "default_user"
        
    # Bind user_id to tools using partial or wrapper, but since we modified tools to accept user_id,
    # we need to make sure the LLM provides it OR we inject it.
    # The cleaner way in LangGraph/LangChain with tool binding is to let LLM generate args,
    # but LLM doesn't know the user_id contextually unless we put it in prompt.
    # However, forcing LLM to output user_id is prone to error.
    # A better way: Partial bind the user_id so LLM only sees other args.
    
    from functools import partial
    from langchain_core.tools import StructuredTool
    
    # We need to wrap the tools to hide 'user_id' from the LLM and inject it.
    # Since we modified the underlying tool function to require user_id,
    # we can create a new tool definition that excludes user_id from schema,
    # and calls the original with injected user_id.
    
    # BUT, the tools.py defined tools using @tool decorator with args_schema.
    # The simplest way now is to update the system prompt to tell LLM to use the provided user_id,
    # OR better: use a custom wrapper here.
    
    # Strategy: Inject user_id into the tools via RunnableConfig
    # We no longer need wrapped functions or custom StructuredTool, 
    # because memory_write/read now take 'config' which LangChain handles.
    
    # We just need to ensure we invoke them with the right config.
    
    # But wait, LLM generates tool calls with 'args' (like {'fact': '...'}).
    # If we call `tool.ainvoke(args, config=...)`, it works.
    
    llm_with_tools = llm.bind_tools([memory_read, memory_write])
    
    messages = state["messages"]
    user_intent = state.get("user_intent")
    
    # Force Tool Use Prompt: Only apply this for MEMORY_READ or ambiguous queries
    # If MEMORY_WRITE, the LLM usually writes correctly without force.
    if user_intent == "MEMORY_READ":
        force_tool_prompt = SystemMessage(content=(
            "You are the Memory Agent. The Supervisor has sent the user here because the query likely involves Personal Memory. "
            "Rules:\n"
            "1. You MUST call `memory_read` to check for personal connections to the query topics (e.g., dates, names) BEFORE answering.\n"
            "2. Even for general questions (e.g., 'What is Dec 30?'), you MUST check if that date has a personal event (like a birthday) attached to it.\n"
            "3. Only answer directly if you have ALREADY called the tool."
        ))
        # Prepend the system prompt to the messages for this turn
        initial_response = await llm_with_tools.ainvoke([force_tool_prompt] + messages)
    else:
        # For MEMORY_WRITE, standard execution
        initial_response = await llm_with_tools.ainvoke(messages)
    
    final_messages = [initial_response]
    
    # 2. Check for Tool Calls
    if initial_response.tool_calls:
        logger.info(f"Memory Agent decided to call tools: {len(initial_response.tool_calls)}")
        
        for tool_call in initial_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]
            
            tool_output = None
            
            # Prepare config with user_id
            config = {"configurable": {"user_id": user_id}}
            
            if tool_name == "memory_write":
                tool_output = await memory_write.ainvoke(tool_args, config=config)
            elif tool_name == "memory_read":
                tool_output = await memory_read.ainvoke(tool_args, config=config)
            
            if tool_output:
                # Add Tool Message
                from langchain_core.messages import ToolMessage
                tool_msg = ToolMessage(content=str(tool_output), tool_call_id=tool_call_id)
                final_messages.append(tool_msg)
        
        # 3. Second LLM Call (Generate Final Answer)
        # We need to append the new messages to the history for the final call
        
        # Synthesis Prompt: Explicitly instruct LLM to combine memory + general knowledge
        synthesis_prompt = SystemMessage(content=(
            "You are a helpful Private Butler. "
            "You have access to the user's personal memory (see the Tool Output above). "
            "Your task is to answer the user's question by SYNTHESIZING their personal memory with your general knowledge.\n"
            "Rules:\n"
            "1. DO NOT reveal the raw tool output, analysis, or 'No info found' messages to the user. These are for your internal reasoning only.\n"
            "2. If the Tool Output contains personal info (e.g., 'Dec 30 is birthday'), explicitly mention it.\n"
            "3. If the user's question also allows for general knowledge (e.g., 'What is Dec 30?'), provide that general context as well.\n"
            "4. If the Tool Output says 'No info found', just answer with your general knowledge or acknowledge the new info if writing.\n"
            "5. Be polite and concise."
        ))
        
        all_messages = [synthesis_prompt] + messages + final_messages
        final_response = await llm.ainvoke(all_messages)
        final_messages.append(final_response)
        
    return {"messages": final_messages}

async def task_agent_node(state: ButlerState):
    """
    Handles task execution (e.g., Search, Email).
    For now, we can give it generic capabilities or placeholder.
    """
    llm = get_llm(temperature=0)
    
    # TODO: Add MCP tools here (Calendar, Email)
    # For now, just a polite response that we are working on it.
    
    prompt = "You are a Task Agent. Currently, external tools (Calendar, Email) are being integrated. Inform the user that you understand the task but cannot execute it yet."
    response = await llm.ainvoke([SystemMessage(content=prompt)] + state["messages"])
    
    return {"messages": [response]}

async def chitchat_node(state: ButlerState):
    """
    Handles casual conversation.
    """
    llm = get_llm(temperature=0.7)
    system_prompt = "You are a helpful, polite Private Butler. Engage in casual conversation with the user."
    response = await llm.ainvoke([SystemMessage(content=system_prompt)] + state["messages"])
    return {"messages": [response]}

async def proactive_node(state: ButlerState):
    """
    Generates a daily briefing.
    """
    # 1. Read from Memory (What's important today?)
    # 2. Check Weather (if tool available)
    # 3. Generate Briefing
    
    logger.info("Generating daily briefing...")
    
    # Simulate gathering context
    # In reality, we would call memory_read.invoke(...)
    
    llm = get_llm(temperature=0.7)
    prompt = (
        "Generate a morning briefing for the user.\n"
        "Include:\n"
        "1. A polite greeting.\n"
        "2. A reminder to check their calendar (simulated).\n"
        "3. A motivational quote."
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {"messages": [response], "daily_briefing": response.content}

# --- Edges ---

def route_supervisor(state: ButlerState):
    intent = state.get("user_intent")
    if intent in ["MEMORY_READ", "MEMORY_WRITE"]:
        return "memory_agent"
    elif intent == "TASK":
        return "task_agent"
    elif intent == "PROACTIVE":
        return "proactive_agent"
    else:
        return "chitchat"

# --- Graph ---

graph_builder = StateGraph(ButlerState)

graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("load_skills", skill_injector.load_skills_context)
graph_builder.add_node("memory_agent", memory_agent_node)
graph_builder.add_node("task_agent", task_agent_node)
graph_builder.add_node("chitchat", chitchat_node)
graph_builder.add_node("proactive_agent", proactive_node)

graph_builder.add_edge(START, "supervisor")
# graph_builder.add_edge("load_skills", "supervisor") # Removed: Skills are now loaded only when needed

graph_builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "memory_agent": "memory_agent",
        "task_agent": "load_skills", # Only load skills if intent is TASK
        "chitchat": "chitchat",
        "proactive_agent": "proactive_agent"
    }
)

graph_builder.add_edge("load_skills", "task_agent")

graph_builder.add_edge("memory_agent", END)
graph_builder.add_edge("task_agent", END)
graph_builder.add_edge("chitchat", END)
graph_builder.add_edge("proactive_agent", END)

# Compile
app = graph_builder.compile()
