import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.config_engine.builder import AgentBuilder
from loguru import logger

async def main():
    """
    测试：从 YAML 配置构建 Agent，并执行一次工作流，输出每步结果。
    """
    load_dotenv()
    
    # Paths to config
    base_path = os.path.join(os.path.dirname(__file__), "../server/config_engine/example_config")
    agents_path = os.path.join(base_path, "agents.yaml")
    tasks_path = os.path.join(base_path, "tasks.yaml")
    
    logger.info("🏗️ Building Agent from YAML...")
    builder = AgentBuilder(agents_path, tasks_path)
    app = builder.build()
    
    logger.info("🚀 Starting Execution...")
    initial_state = {"results": {}}
    
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
