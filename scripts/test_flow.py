import sys
import os
from langchain_core.messages import HumanMessage

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.kernel.master_graph import build_master_graph

async def run_test(input_text: str, expected_plugin: str):
    print(f"\n--- Testing Input: '{input_text}' ---")
    
    master_graph = build_master_graph()
    
    # 构建初始状态
    initial_state = {
        "messages": [HumanMessage(content=input_text)],
        "target_plugin": "" # 初始为空
    }
    
    try:
        # 调用 master_graph
        result = await master_graph.ainvoke(initial_state)
        
        # 检查路由结果
        # 注意：最终结果可能不是 target_plugin，因为 Graph 运行完了。
        # 我们可能需要检查 execution trace 或者 log。
        # 这里简单打印结果看看
        print(f"Graph finished. Result keys: {result.keys()}")
        if "plan" in result:
             print(f"Plan: {result['plan']}")
             
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    import asyncio
    # Test Case 1: Tutorial
    asyncio.run(run_test("I want to learn Python", "tutorial_agent"))
    
    # Test Case 2: FTA
    # asyncio.run(run_test("Analyze this engine fire", "fta_analyst"))
