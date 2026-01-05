from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from server.core.config import settings
import sys
import asyncio
from sqlalchemy.exc import DBAPIError
from loguru import logger

# Construct Async Database URL (driver: postgresql+asyncpg)
# If no DATABASE_URL is provided, we might fail or fallback.
# For now, let's assume it will be provided or we handle it gracefully.
# The original main.py handles it by not initing DB if missing.
# But for User Auth, we NEED a DB.
# Let's fallback to sqlite+aiosqlite if postgres is not configured, to allow local dev without postgres easily?
# But user specifically asked for postgres in rules.
# Let's stick to what we have. If DATABASE_URL is None, create_async_engine might fail or we create a dummy one.

database_url = settings.DATABASE_URL
if not database_url:
    # Fallback to postgres to match server.db.session default
    # Was: database_url = "sqlite+aiosqlite:///./sql_app.db"
    database_url = "postgresql+asyncpg://user:password@localhost:5432/seerlord"
else:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    session: AsyncSession = SessionLocal()
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        except Exception as e:
            logger.warning(f"DB rollback failed: {e}")
        raise
    finally:
        try:
            await session.close()
        except asyncio.CancelledError:
            try:
                await asyncio.shield(session.close())
            except Exception:
                pass
            raise
        except DBAPIError as e:
            logger.warning(f"DB session close failed: {e}")
        except Exception as e:
            logger.warning(f"DB session close failed: {e}")
