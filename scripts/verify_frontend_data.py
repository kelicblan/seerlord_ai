import httpx
import json
import sys
import asyncio
from loguru import logger

# URL for the LangServe stream endpoint
URL = "http://localhost:8001/api/v1/agent/stream_events"

async def main():
    """
    验证前端/后端对接的关键接口是否可用（主要用于本地冒烟检查）。
    """
    logger.info(f"连接到流式接口：{URL}")
    
    # Input payload
    payload = {
        "input": {
            "messages": [{"type": "human", "content": "What are the major news headlines today?"}]
        },
        "config": {
            "configurable": {"thread_id": "test_verification"}
        }
    }

    # try:
    #     async with httpx.AsyncClient(timeout=60.0) as client:
    #         async with client.stream("POST", URL, json=payload) as response:
    #             print(f"Status Code: {response.status_code}")
    #             if response.status_code != 200:
    #                 print("Failed to connect.")
    #                 return

    #             print("\n--- Streaming Events ---\n")
                
    #             async for line in response.aiter_lines():
    #                 if not line or not line.strip():
    #                     continue
                    
    #                 if line.startswith("event:"):
    #                     event_type = line.split(":", 1)[1].strip()
    #                     # print(f"Event Type: {event_type}")
                    
    #                 if line.startswith("data:"):
    #                     data_str = line.split(":", 1)[1].strip()
    #                     try:
    #                         data = json.loads(data_str)
                            
    #                         # We are looking for specific updates in the state
    #                         event = data.get("event")
                            
    #                         # Filter for relevant events
    #                         if event == "on_chain_end":
    #                             # Check if this is a node output
    #                             output = data.get("data", {}).get("output")
    #                             if output and isinstance(output, dict):
    #                                 # Check for Plan
    #                                 if "plan" in output:
    #                                     print("\n[✅ PLAN DETECTED]")
    #                                     print(json.dumps(output["plan"], indent=2, ensure_ascii=False))
                                    
    #                                 # Check for Progress
    #                                 if "current_step_index" in output:
    #                                     idx = output["current_step_index"]
    #                                     print(f"\n[✅ PROGRESS UPDATE] Step Index: {idx}")
                                    
    #                                 # Check for Feedback/Critique
    #                                 if "feedback_history" in output:
    #                                     print(f"\n[✅ CRITIQUE DETECTED] Feedback: {output['feedback_history']}")

    #                         # Also print the raw event name so we know what's happening
    #                         # print(f"Event: {event}")
                            
    #                     except json.JSONDecodeError:
    #                         print(f"Raw Data: {data_str}")
                            
    # except Exception as e:
    #     print(f"Error during stream: {e}")

    # Verify Master Graph Endpoint
    GRAPH_URL = "http://localhost:8001/api/v1/agent/master/graph"
    logger.info(f"连接到 Master Graph 接口：{GRAPH_URL}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(GRAPH_URL)
            if resp.status_code == 200:
                data = resp.json()
                if "mermaid" in data:
                    mermaid = data.get("mermaid") or ""
                    logger.success("已获取 Master Graph Mermaid")
                    logger.info(f"Mermaid 长度：{len(mermaid)} chars")
                    logger.info(f"Mermaid 开头：{mermaid[:50]}...")
                else:
                    logger.error(f"响应缺少 mermaid 字段：{data}")
            else:
                logger.error(f"请求失败：status={resp.status_code} body={resp.text}")
    except Exception as e:
        logger.error(f"获取 Master Graph 失败：{e}")

if __name__ == "__main__":
    asyncio.run(main())
