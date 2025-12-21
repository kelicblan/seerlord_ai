import requests
import json
import time
from loguru import logger

BASE_URL = "http://127.0.0.1:8000"
API_V1_URL = f"{BASE_URL}/api/v1/paas"

# Test Data
TENANT_A_KEY = "sk-construction-app"
TENANT_B_KEY = "sk-learning-tutor"
INVALID_KEY = "sk-invalid-key"

# Minimal Valid Config
TEST_CONFIG = {
    "agents": {
        "echo_bot": {
            "role": "Echo Bot",
            "goal": "Echo back the input",
            "backstory": "I am a simple bot.",
            "verbose": True
        }
    },
    "tasks": [
        {
            "id": "echo_task",
            "description": "Say 'Hello World'",
            "expected_output": "Hello World",
            "agent": "echo_bot"
        }
    ]
}

def test_unauthorized_access():
    """
    测试：不携带 API Key 时，是否被正确拦截。
    """
    logger.info("测试未授权访问（无 X-API-Key）")
    try:
        response = requests.post(
            f"{API_V1_URL}/execute", 
            json={"config": TEST_CONFIG}
        )
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.json()}")
        if response.status_code == 401 or response.status_code == 403:
            logger.success("未授权访问已正确拦截")
        else:
            logger.error("未授权访问未被拦截（预期 401/403）")
    except Exception as e:
        logger.error(f"请求异常：{e}")

def test_invalid_key_access():
    """
    测试：携带无效 API Key 时，是否返回 403。
    """
    logger.info("测试无效 API Key 访问")
    try:
        response = requests.post(
            f"{API_V1_URL}/execute", 
            json={"config": TEST_CONFIG},
            headers={"X-API-Key": INVALID_KEY}
        )
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.json()}")
        if response.status_code == 403:
            logger.success("无效 API Key 已正确拦截（403）")
        else:
            logger.error("无效 API Key 未按预期返回 403")
    except Exception as e:
        logger.error(f"请求异常：{e}")

def test_valid_tenant_access(tenant_name, api_key):
    """
    测试：携带有效租户 API Key 时，是否能成功创建执行任务。
    """
    logger.info(f"测试有效租户访问：{tenant_name}")
    try:
        response = requests.post(
            f"{API_V1_URL}/execute", 
            json={"config": TEST_CONFIG},
            headers={"X-API-Key": api_key}
        )
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if "execution_id" in data:
                logger.success(f"请求已受理：execution_id={data['execution_id']}")
            else:
                logger.error("响应缺少 execution_id")
        else:
            logger.error(f"请求失败：status={response.status_code}")
    except Exception as e:
        logger.error(f"请求异常：{e}")

if __name__ == "__main__":
    logger.info("等待服务启动完成...")
    time.sleep(2) 
    
    test_unauthorized_access()
    test_invalid_key_access()
    test_valid_tenant_access("Tenant A (Construction)", TENANT_A_KEY)
    test_valid_tenant_access("Tenant B (Tutor)", TENANT_B_KEY)
