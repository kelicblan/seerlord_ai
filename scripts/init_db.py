import sys
import os
from loguru import logger

# Add project root to sys.path
sys.path.append(os.getcwd())

from server.db.session import engine, Base
from server.db.models import Tenant, Skill

def init_db():
    """
    初始化本地数据库表结构（同步 SQLAlchemy 引擎版本）。
    """
    logger.info("开始创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.success("数据库表创建完成！")

if __name__ == "__main__":
    init_db()
