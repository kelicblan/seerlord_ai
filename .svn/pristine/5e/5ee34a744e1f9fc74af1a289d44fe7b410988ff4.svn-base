import sys
import os
from pathlib import Path
from loguru import logger

# 添加项目根目录到 sys.path
sys.path.insert(0, os.getcwd())

# Mock 环境变量以通过 Config 验证
os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-validation"

def verify_system():
    logger.info("开始验证 SeerLord AI 内核...")
    
    try:
        from server.core.config import settings
        logger.info(f"配置加载成功: PROJECT_NAME={settings.PROJECT_NAME}")
        
        from server.kernel.registry import registry
        logger.info("正在扫描插件...")
        registry.scan_and_load()
        logger.info(f"已加载插件: {list(registry.plugins.keys())}")
        
        from server.kernel.master_graph import build_master_graph
        logger.info("正在构建 Master Graph...")
        graph = build_master_graph()
        logger.info("Master Graph 构建成功！")
        
        # 打印 Graph 的结构（简单的）
        logger.info(f"Graph Nodes: {graph.nodes.keys()}")
        
        logger.success("所有系统检查通过！核心架构正常。")
        
    except Exception as e:
        logger.exception(f"验证失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_system()
