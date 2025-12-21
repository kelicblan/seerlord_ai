import httpx
import json
import asyncio
import sys
from loguru import logger

URL = "http://localhost:8000/api/v1/agent/stream_events"
API_KEY = "sk-admin-test"

PROMPT = """
我要40天内学会脱口讲英语和听得懂英语日常对话。
给我列出学习的计划，按每天早晚各学习40分钟的量来计划。
先规划，然后组织学习素材，我只需要跟着步骤学习即可达到目标。
注意几项必须有：
1、计划分阶段，但是必须具体到每天学习什么，和详细的学习内容，不需要我再去找资料；
2、音标，所有单词都需要加上音标；
3、有英文的地方右边都有一个语音播放按钮，点击播放读音 (可以用 [🔊] 代替)；
4、以美式英语读音为主；
5、发音技巧，总结出常用单词的发音技巧，最终实现陌生单词也会根据技巧来读。
"""

async def main():
    """
    通过 SSE 流式接口请求后端生成英语学习计划，并实时打印生成内容。
    """
    logger.info(f"正在发送请求：{URL}")
    
    payload = {
        "input": {
            "input": PROMPT,
            "target_plugin": "tutorial_agent"
        },
        "config": {"configurable": {"thread_id": "english_plan_001"}}
    }
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", URL, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"请求失败：status={response.status_code} body={await response.aread()}")
                    return

                logger.info("开始生成计划（流式输出）")
                
                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue
                    
                    if line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()
                        try:
                            data = json.loads(data_str)
                            event_type = data.get("event")
                            
                            # DEBUG: Print everything
                            # print(f"Event: {event_type} | Name: {data.get('name')}")
                            
                            if event_type == "on_chat_model_stream":
                                chunk = data.get("data", {}).get("chunk", {})
                                content = chunk.get("content", "")
                                if content:
                                    sys.stdout.write(content)
                                    sys.stdout.flush()
                            elif event_type == "on_chain_end":
                                # Print final outputs if available
                                output = data.get("data", {}).get("output")
                                if output and isinstance(output, dict) and "results" in output:
                                    result_text = output['results']
                                    # Handle case where results is a dict (node_id -> content)
                                    if isinstance(result_text, dict):
                                        # Join all values
                                        result_text = "\n\n".join([str(v) for v in result_text.values()])
                                    
                                    logger.success("已生成最终结果")
                                    logger.opt(raw=True).info(f"\n\n[Result]: {result_text}\n")
                                    
                                    # Save to file
                                    with open("english_learning_plan.md", "w", encoding="utf-8") as f:
                                        f.write(str(result_text))
                                    logger.success("已保存到 english_learning_plan.md")
                                    
                                elif output and isinstance(output, str):
                                    logger.opt(raw=True).info(f"\n[Output]: {output}\n")
                                    
                        except Exception as e:
                            logger.warning(f"解析行失败：{line[:50]}... err={e}")
                            
    except Exception as e:
        logger.error(f"连接失败：{e}")

if __name__ == "__main__":
    asyncio.run(main())
