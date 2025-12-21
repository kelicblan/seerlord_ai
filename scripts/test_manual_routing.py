
import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.kernel.registry import registry
from server.kernel.master_graph import planner_node, MasterState, Task
from langchain_core.messages import HumanMessage
from loguru import logger

async def test_manual_routing():
    # 1. Initialize Registry
    logger.info("Scanning plugins...")
    registry.scan_and_load()
    
    # 2. Define Test Cases
    test_cases = [
        {
            "input": "Tell me the latest news about AI.",
            "target_plugin": "tutorial_agent", # Intentionally wrong mapping to test override
            "expected_plugin": "tutorial_agent"
        },
        {
            "input": "I want to learn English.",
            "target_plugin": "news_reporter", # Intentionally wrong mapping
            "expected_plugin": "news_reporter"
        },
        {
            "input": "General chat",
            "target_plugin": "auto",
            "expected_plugin": "planner_logic" # Should go to standard planner logic (likely chitchat or planner)
        }
    ]
    
    for case in test_cases:
        logger.info(f"\n--- Testing Manual Override: {case['target_plugin']} ---")
        
        # Construct State
        state: MasterState = {
            "messages": [HumanMessage(content=case["input"])],
            "target_plugin": case["target_plugin"],
            "session_id": "test_session",
            "agent_name": "test_agent"
        }
        
        # Run Planner Node
        # We need to mock config
        config = {"configurable": {"thread_id": "test"}}
        
        if case["target_plugin"] == "auto":
             # For 'auto', we expect the planner to actually run the LLM, 
             # but we don't want to waste tokens/time here, so we just check if it DOESN'T return the manual plan immediately.
             # Actually, if we run it, it might call LLM.
             # Let's just skip execution for auto or expect it to NOT be the manual plan structure.
             logger.info("Skipping execution for 'auto' to avoid LLM call in unit test, assume standard path.")
             continue

        result = await planner_node(state, config)
        
        plan = result.get("plan")
        if plan:
            first_task = plan.tasks[0]
            logger.info(f"Generated Task Plugin: {first_task.plugin_name}")
            
            if first_task.plugin_name == case["expected_plugin"]:
                logger.success(f"✅ PASSED: Routed to {case['expected_plugin']} as requested.")
            else:
                logger.error(f"❌ FAILED: Expected {case['expected_plugin']}, got {first_task.plugin_name}")
        else:
            logger.error("❌ FAILED: No plan generated.")

if __name__ == "__main__":
    asyncio.run(test_manual_routing())
