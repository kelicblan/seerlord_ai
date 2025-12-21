import asyncio
import sys
import os
from loguru import logger
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage

# Add project root to path
sys.path.append(os.getcwd())

from server.core.config import settings
from server.kernel.memory_manager import memory_manager
from server.kernel.dynamic_skill_manager import dynamic_skill_manager

async def test_event_stream():
    """
    Verify that skill retrieval and evolution emit custom events.
    """
    logger.info("Initializing system...")
    await memory_manager.initialize()
    
    if not memory_manager.enabled:
        logger.error("Memory disabled. skipping.")
        return

    # Wrap the manager call in a RunnableLambda to capture events
    # Because dispatch_custom_event works within a Runnable context
    
    async def invoke_manager(input_dict):
        query = input_dict["query"]
        skill, reason = await dynamic_skill_manager.get_or_evolve_skill(query)
        return {"skill": skill.name, "reason": reason}

    runnable = RunnableLambda(invoke_manager)
    
    query = "How do I make a cup of tea?" # Something new to trigger evolution potentially, or just retrieval
    
    logger.info(f"\n--- Streaming Events for Query: '{query}' ---")
    
    async for event in runnable.astream_events({"query": query}, version="v2"):
        event_name = event["event"]
        
        # We are looking for 'on_custom_event'
        if event_name == "on_custom_event":
            custom_event_name = event["name"]
            data = event["data"]
            logger.success(f"🔔 Custom Event Captured: {custom_event_name} | Data: {data}")
        
        # Also print standard events to see flow
        elif event_name == "on_chain_start":
             logger.debug(f"Chain Start: {event['name']}")

if __name__ == "__main__":
    if not settings.OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY found. Evolution might fail.")
    
    asyncio.run(test_event_stream())
