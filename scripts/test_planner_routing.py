import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[1]))

from server.kernel.registry import registry
from server.kernel.master_graph import planner_node, MasterState, MasterPlan
from langchain_core.messages import HumanMessage
from loguru import logger

async def test_planner_routing():
    """
    测试：验证 Planner 是否能在插件列表中正确路由到合适的插件。
    """
    # 1. Load Plugins
    registry.scan_and_load()
    logger.info(f"已加载插件：{list(registry.plugins.keys())}")
    
    # 2. Simulate User Request
    user_request = (
        "我要40天内学会脱口讲英语和听得懂英语日常对话。 "
        "给我列出学习的计划，按每天早晚各学习40分钟的量来计划。 "
        "注意几项必须有： "
        "1、计划分阶段，但是必须具体到每天学习什么，和详细的学习内容； "
        "2、音标，所有单词都需要加上音标； "
        "3、有英文的地方右边都有一个语音播放按钮，点击播放读音； "
        "4、以美式英语读音为主； "
        "5、发音技巧，总结出常用单词的发音技巧。"
    )
    
    state = {
        "messages": [HumanMessage(content=user_request)],
        "session_id": "test_session",
        "agent_name": "test_agent"
    }
    
    # 3. Run Planner Node
    logger.info("开始运行 Planner 节点")
    result = await planner_node(state, {})
    
    plan: MasterPlan = result.get("plan")
    
    if not plan:
        logger.error("规划失败：未生成 plan")
        return
        
    logger.info(f"生成计划任务数：{len(plan.tasks)}")
    for task in plan.tasks:
        logger.info(f"Task {task.id}: [{task.plugin_name}] - {task.description}")
        
    # Check if Voyager was selected
    voyager_selected = any(t.plugin_name == "voyager_agent" for t in plan.tasks)
    
    if voyager_selected:
        logger.success("SUCCESS：Voyager Agent 被成功选中")
    else:
        logger.warning("FAILURE：Voyager Agent 未被选中")
        # If failure, print descriptions to debug
        logger.info("Planner 看到的插件描述如下：")
        for name, p in registry.plugins.items():
            logger.info(f"- {name}: {p.description}")

if __name__ == "__main__":
    asyncio.run(test_planner_routing())
