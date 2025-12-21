import requests
from loguru import logger

def check_api():
    """
    检查后端插件列表接口是否可用，并打印返回结果。
    """
    url = "http://127.0.0.1:8000/api/v1/plugins"
    logger.info(f"开始检查接口：{url}")
    try:
        response = requests.get(url, timeout=5)
        logger.info(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Data: {data}")
            if len(data) == 0:
                logger.warning("接口返回空列表（可能尚未加载插件或服务未就绪）")
            else:
                logger.success(f"接口正常：发现 {len(data)} 个插件")
        else:
            logger.error(f"接口异常：Unexpected status code {response.status_code}")
            logger.error(response.text)
    except Exception as e:
        logger.error(f"连接失败：{e}")
        logger.info("请确认后端服务是否在 8000 端口运行")

if __name__ == "__main__":
    check_api()
