import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config_engine.builder import AgentBuilder
from server.kernel.mcp_manager import mcp_manager
from loguru import logger

async def main():
    """
    测试：加载 MCP 配置后，从示例 YAML 构建 Agent 并执行一次工作流。
    """
    load_dotenv()
    
    # Initialize MCP
    mcp_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../mcp.json"))
    logger.info(f"🔌 Initializing MCP from {mcp_config_path}")
    await mcp_manager.load_config(mcp_config_path)
    
    # Paths to config
    base_path = os.path.join(os.path.dirname(__file__), "../server/plugins/_example_agent")
    config_path = os.path.join(base_path, "config.yaml")
    
    logger.info(f"🏗️ Building Agent from YAML at {config_path}...")
    # Using same file for agents and tasks
    builder = AgentBuilder(config_path, config_path)
    app = builder.build()
    
    logger.info("🚀 Starting Execution with Input: 'Research the impact of AI on software engineering jobs'")
    initial_state = {
        "results": {},
        "input": "Research the impact of AI on software engineering jobs in 2024."
    }
    
    async for event in app.astream(initial_state):
        for key, value in event.items():
            logger.info(f"Step Completed: {key}")
            if "results" in value and key in value["results"]:
                logger.opt(raw=True).info(
                    f"\n--- {key} 输出结果 ---\n{value['results'][key]}\n-----------------------------"
                )

    logger.info("🎉 Workflow Finished!")

if __name__ == "__main__":
    asyncio.run(main())
