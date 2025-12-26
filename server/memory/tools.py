from typing import Annotated, Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage
from loguru import logger

from server.memory.manager import MemoryManager
from server.memory.schemas import MemoryType

# --- Tools ---

@tool
async def remember_fact(
    fact: Annotated[str, "The important fact, preference, or plan to remember about the user."],
    user_id: Annotated[str, "The ID of the user."] = "default_user"
):
    """
    Use this tool to explicitly record important information mentioned by the user, 
    such as their profession, preferences, future plans, or specific constraints.
    Do NOT use this for general conversation history (which is saved automatically).
    """
    manager = await MemoryManager.get_instance()
    await manager.add_semantic_knowledge(content=fact, user_id=user_id)
    return f"Fact remembered: {fact}"

@tool
async def recall_past(
    query: Annotated[str, "The search query to find relevant past interactions or facts."],
    user_id: Annotated[str, "The ID of the user."] = "default_user"
):
    """
    Use this tool to search for specific details from past conversations or user profile 
    when the current context is insufficient.
    """
    manager = await MemoryManager.get_instance()
    context_dict = await manager.retrieve_context(query=query, user_id=user_id)
    
    if not context_dict["profile"] and not context_dict["memories"]:
        return "No relevant memories found."
        
    parts = []
    if context_dict["profile"]:
        parts.append("### User Profile:")
        parts.extend([f"- {p}" for p in context_dict["profile"]])
    
    if context_dict["memories"]:
        parts.append("\n### Relevant Past Events:")
        parts.extend([f"- {m}" for m in context_dict["memories"]])
        
    return "\n".join(parts)

# --- LangGraph Node ---

async def memory_node(state: Dict[str, Any]):
    """
    LangGraph Node: Load memory context before generating response.
    Expects state to have 'messages' (List[BaseMessage]) and 'user_id' (str).
    Updates state with 'memory_context' (str).
    """
    messages = state.get("messages", [])
    user_id = state.get("user_id", "default_user")
    
    if not messages:
        return {"memory_context": ""}
        
    # Find the last human message to use as query
    last_human_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    
    if not last_human_msg:
        return {"memory_context": ""}
        
    query = last_human_msg.content
    
    logger.info(f"🧠 Memory Node: Retrieving context for query: {query[:50]}...")
    
    manager = await MemoryManager.get_instance()
    context_dict = await manager.retrieve_context(query=query, user_id=user_id)
    
    # Format for Agent Prompt
    parts = []
    if context_dict["profile"]:
        parts.append("### User Profile:")
        parts.extend([f"- {p}" for p in context_dict["profile"]])
    
    if context_dict["memories"]:
        parts.append("\n### Relevant Past Events:")
        parts.extend([f"- {m}" for m in context_dict["memories"]])
        
    context_str = "\n".join(parts)
    
    return {"memory_context": context_str}
