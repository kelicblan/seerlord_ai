from typing import Tuple
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from loguru import logger

async def init_postgres_checkpointer(database_url: str) -> Tuple[AsyncPostgresSaver, AsyncConnectionPool]:
    """
    初始化 PostgreSQL Checkpointer。
    
    Returns:
        Tuple[AsyncPostgresSaver, AsyncConnectionPool]: 返回 checkpointer 和连接池。
        注意：调用者必须负责在应用关闭时关闭连接池 (pool.close())。
    """
    logger.info("Initializing PostgreSQL Checkpointer...")
    
    pool = AsyncConnectionPool(
        conninfo=database_url,
        max_size=20,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    
    # 显式打开连接池（虽然 AsyncConnectionPool 通常在 enter 时打开，但这里我们需要手动控制）
    await pool.open()
    
    checkpointer = AsyncPostgresSaver(pool)
    
    # 首次运行时创建必要的表
    await checkpointer.setup()
    
    logger.info("PostgreSQL Checkpointer ready.")
    return checkpointer, pool
