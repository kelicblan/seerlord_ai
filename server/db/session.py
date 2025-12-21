from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from server.core.config import settings

def _build_sync_database_url() -> str:
    """
    构造同步 SQLAlchemy 连接串（用于同步 SessionLocal）。
    说明：
    - 优先使用 psycopg(v3) 驱动，避免在环境中缺少 psycopg2 导致导入失败。
    - 若用户未配置 `DATABASE_URL`，使用本地默认 Postgres 连接串。
    """
    database_url = settings.DATABASE_URL or "postgresql://user:password@localhost:5432/seerlord"
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    return database_url

engine = create_engine(_build_sync_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
