from typing import Optional
import httpx
import asyncio
import base64
from loguru import logger
from langchain_core.tools import tool
from server.core.llm import get_active_model_config

@tool
async def generate_image_base64(prompt: str) -> Optional[str]:
    """
    根据提示词生成图片，返回 Base64 字符串。
    使用系统配置的文生图模型 (TEXT_TO_IMAGE_MODEL_ID)。
    支持 OpenAI 兼容接口和阿里云 DashScope 原生接口。
    """
    try:
        # 1. 获取模型配置
        model_config = get_active_model_config("TEXT_TO_IMAGE_MODEL_ID")
        
        if not model_config:
            logger.warning("No active image generation model configured. Skipping.")
            return None

        logger.info(f"Generating image with model: {model_config.name} ({model_config.model_name})")

        api_key = model_config.api_key or "sk-dummy"
        base_url = model_config.base_url.rstrip("/") if model_config.base_url else "https://api.openai.com/v1"

        # === 2. DashScope Native Logic ===
        # 如果 URL 包含 dashscope 且看起来像原生 endpoint，或者之前探测发现不兼容
        # 我们优先尝试检测是否为原生接口调用
        is_dashscope_native = "dashscope.aliyuncs.com" in base_url and "compatible-mode" not in base_url
        
        if is_dashscope_native:
            return await _generate_dashscope_native(api_key, base_url, model_config.model_name, prompt)

        # === 3. OpenAI Compatible Logic ===
        # 智能 URL 处理
        if base_url.endswith("/generation") or base_url.endswith("/generations"):
             url = base_url
        else:
             if not base_url.endswith("/v1"):
                 if "/v1" not in base_url:
                     base_url += "/v1"
             url = f"{base_url}/images/generations"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_config.model_name,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"OpenAI Image Gen failed: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                b64_str = data["data"][0].get("b64_json")
                if b64_str:
                    logger.info("Image generated successfully (OpenAI Mode).")
                    return b64_str
            
            logger.error(f"Unexpected response format: {data}")
            return None

    except Exception as e:
        logger.error(f"Error during image generation: {e}")
        return None

async def _generate_dashscope_native(api_key: str, base_url: str, model_name: str, prompt: str) -> Optional[str]:
    """
    处理阿里云 DashScope 原生异步调用逻辑
    """
    logger.info("Using DashScope Native Mode")
    
    # 修正 endpoint: 如果 base_url 已经是 endpoint，直接用；否则拼凑
    if base_url.endswith("/generation"):
        url = base_url
    else:
        # 默认 endpoint
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        if "multimodal-generation" in base_url:
             # 如果配置里有 multimodal-generation，就信它
             if not base_url.endswith("/generation"):
                  url = f"{base_url}/generation"
             else:
                  url = base_url
    
    # DashScope Header
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable" # 强制异步
    }
    
    # DashScope Payload
    # 注意：如果 model_name 是 z-image-turbo，DashScope 可能不认。
    # 通常是 wanx-v1。我们先试用 model_name，如果报错再 fallback 到 wanx-v1
    payload = {
        "model": model_name if model_name.startswith("wanx") else "wanx-v1", 
        "input": {
            "prompt": prompt
        },
        "parameters": {
            "style": "<auto>",
            "size": "1024*1024",
            "n": 1
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 提交任务
        resp = await client.post(url, json=payload, headers=headers)
        
        # Fallback: 如果配置的 URL 不可用（如 400 URL Error），尝试使用标准 DashScope 文生图 Endpoint
        if resp.status_code in [400, 404]:
             logger.warning(f"DashScope submit failed with URL {url} (Status: {resp.status_code}). Trying standard endpoint.")
             url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
             resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(f"DashScope submit failed: {resp.status_code} - {resp.text}")
            return None
        
        task_data = resp.json()
        task_id = task_data.get("output", {}).get("task_id")
        if not task_id:
            logger.error(f"No task_id in DashScope response: {task_data}")
            return None
            
        logger.info(f"DashScope task submitted: {task_id}")
        
        # 2. 轮询任务状态
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for _ in range(30): # 最多轮询 30 次，每次 2 秒 -> 60秒超时
            await asyncio.sleep(2)
            task_resp = await client.get(task_url, headers={"Authorization": f"Bearer {api_key}"})
            
            if task_resp.status_code != 200:
                logger.error(f"DashScope poll failed: {task_resp.status_code}")
                continue
                
            task_res = task_resp.json()
            status = task_res.get("output", {}).get("task_status")
            
            if status == "SUCCEEDED":
                # 3. 下载图片
                results = task_res.get("output", {}).get("results", [])
                if results and "url" in results[0]:
                    img_url = results[0]["url"]
                    logger.info(f"Downloading image from {img_url}")
                    img_resp = await client.get(img_url)
                    if img_resp.status_code == 200:
                        b64_str = base64.b64encode(img_resp.content).decode("utf-8")
                        logger.info("Image downloaded and converted to base64")
                        return b64_str
                logger.error("No image URL in succeeded task")
                return None
                
            elif status in ["FAILED", "CANCELED"]:
                logger.error(f"DashScope task failed: {task_res}")
                return None
                
        logger.error("DashScope task timed out")
        return None
