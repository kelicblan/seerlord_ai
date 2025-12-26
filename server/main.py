import sys
import asyncio
import os
from pathlib import Path

# 兼容直接运行 `python server/main.py`：确保项目根目录在 sys.path 中
repo_root_for_import = Path(__file__).resolve().parents[1]
if str(repo_root_for_import) not in sys.path:
    sys.path.insert(0, str(repo_root_for_import))

# Windows 下 psycopg 异步需要 SelectorEventLoop（必须在事件循环启动前设置）
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from loguru import logger
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    AsyncPostgresSaver = None
    logger.warning("Module 'langgraph.checkpoint.postgres.aio' not found. PostgreSQL persistence will be unavailable.")

from psycopg_pool import AsyncConnectionPool
import uvicorn

from server.core.config import settings
from server.kernel.registry import registry
from server.kernel.master_graph import build_master_graph
from server.kernel.mcp_manager import mcp_manager
from server.memory.manager import MemoryManager
from server.api.auth import TenantMiddleware
from server.api.v1 import paas_agent, agent, login, users, skills, tools, files, knowledge, artifact, api_keys, settings as settings_api
from server.core.database import engine, Base, SessionLocal
from anyio import to_thread

# -----------------------------------------------------------------------------
# Global Resources
# -----------------------------------------------------------------------------
# Placeholder for global checkpointer
checkpointer = MemorySaver()

# -----------------------------------------------------------------------------
# Master Graph Setup (Lazy / Pre-init)
# -----------------------------------------------------------------------------
# 1. 扫描插件
logger.info("Scanning and loading plugins...")
registry.scan_and_load()

# 2. 构建 Master Graph
# Initial build with MemorySaver. Will be upgraded to Postgres in lifespan if configured.
master_graph = build_master_graph(checkpointer)

# -----------------------------------------------------------------------------
# Lifespan Events
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期钩子：负责启动/关闭阶段的资源初始化与释放。
    主要工作：
    - 初始化（可选）PostgreSQL Checkpointer，用于 LangGraph 持久化
    - 初始化 Qdrant 记忆库
    - 初始化 MCP 外部工具连接
    - 初始化用户表结构（不再创建默认管理员，改为首启初始化接口）
    """
    logger.info("Starting SeerLord AI Kernel...")
    
    # 1. Database Connection Management
    if settings.DATABASE_URL:
        should_init_postgres_checkpointer = True
        if sys.platform == "win32":
            running_loop = asyncio.get_running_loop()
            if running_loop.__class__.__name__ == "ProactorEventLoop":
                should_init_postgres_checkpointer = False
                logger.warning("检测到 Windows ProactorEventLoop，psycopg 异步不兼容，将跳过 PostgreSQL Checkpointer 初始化")

        if should_init_postgres_checkpointer:
            if AsyncPostgresSaver is None:
                logger.warning("AsyncPostgresSaver is unavailable (import failed). Falling back to In-Memory persistence.")
            else:
                logger.info("Opening Database Connection Pool...")
                try:
                    pool = AsyncConnectionPool(
                        conninfo=settings.DATABASE_URL,
                        max_size=20,
                        open=False, # We will open it manually
                        kwargs={
                            "autocommit": True,
                            "prepare_threshold": 0,
                        },
                        min_size=1,
                        max_lifetime=300, # Recycle connections every 5 minutes
                        timeout=30, # Wait at most 30s for a connection
                        check=AsyncConnectionPool.check_connection 
                    )
                    await pool.open()
                    
                    logger.info("Initializing PostgreSQL Checkpointer...")
                    real_checkpointer = AsyncPostgresSaver(pool)
                    
                    # Initialize tables if needed
                    await real_checkpointer.setup()
                    
                    # Hot-Swap Checkpointer in Compiled Graph
                    logger.info("Swapping Master Graph Checkpointer to PostgreSQL...")
                    master_graph.checkpointer = real_checkpointer
                    
                    # Store pool in app state for cleanup
                    app.state.db_pool = pool
                    
                except Exception as e:
                    logger.error(f"Failed to initialize Database: {e}")
                    logger.warning("System running with In-Memory persistence (Data will be lost on restart)")
        else:
            logger.warning("System running with In-Memory persistence (Data will be lost on restart)")
    else:
        logger.warning("No DATABASE_URL found. System running with In-Memory persistence.")
    
    # 2. Initialize Memory Manager (Qdrant)
    logger.info("Initializing Memory Manager (Qdrant)...")
    await MemoryManager.get_instance()

    # 3. Initialize MCP Manager
    # MCP 配置文件默认在项目根目录，避免工作目录变化导致找不到配置
    repo_root = Path(__file__).resolve().parents[1]
    mcp_config_path = repo_root / "server/mcp.json"
    if mcp_config_path.exists():
        logger.info(f"Initializing MCP Manager from {mcp_config_path}...")
        await mcp_manager.load_config(str(mcp_config_path))
    else:
        logger.info(f"No mcp.json found at {mcp_config_path}, skipping MCP initialization.")
    
    # 4. Initialize User DB
    logger.info("Initializing User Database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Initializing Sync SQLAlchemy Database...")
    try:
        from server.db.session import engine as sync_engine
        from server.db.session import Base as SyncBase

        def _init_sync_tables() -> None:
            import server.db.models

            SyncBase.metadata.create_all(bind=sync_engine)

        await to_thread.run_sync(_init_sync_tables)
    except Exception as e:
        logger.error(f"Failed to initialize Sync SQLAlchemy tables: {e}")
        logger.warning("Sync SQLAlchemy tables are not initialized. Related APIs may fail.")

    yield
    
    # Cleanup
    logger.info("Shutting down SeerLord AI Kernel...")
    if hasattr(app.state, "db_pool"):
        logger.info("Closing Database Connection Pool...")
        await app.state.db_pool.close()

    # 关闭 MCP 子进程/会话，避免热重载或退出时残留
    try:
        await mcp_manager.close_all()
    except Exception as e:
        logger.warning(f"Failed to close MCP sessions cleanly: {e}")

app = FastAPI(
    title="SeerLord AI Kernel",
    version="1.0.0",
    description="Micro-Kernel Agent Orchestration Platform",
    lifespan=lifespan
)

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.get("/api/v1/plugins")
async def get_plugins():
    """Get list of available agent plugins"""
    plugins = []
    for pid, plugin in registry._plugins.items():
        if pid.startswith("_"):
            continue
            
        plugins.append({
            "id": pid,
            "name": plugin.name,
            "name_zh": plugin.name_zh,
            "description": plugin.description,
            "type": "application"
        })
    return plugins

@app.get("/api/v1/mcp/status", dependencies=[Depends(login.get_current_user)])
async def get_mcp_status():
    """Get status of MCP servers and tools"""
    # Use the manager's summary method which has accurate tool counts
    return mcp_manager.get_status_summary()

@app.get("/api/v1/agent/{agent_id}/graph")
async def get_agent_graph(agent_id: str):
    """Get Mermaid graph definition for an agent"""
    plugin = registry.get_plugin(agent_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    try:
        graph = plugin.get_graph()
        mermaid = graph.get_graph().draw_mermaid()
        return {"mermaid": mermaid}
    except Exception as e:
        logger.error(f"Failed to generate graph for {agent_id}: {e}")
        return {"mermaid": None, "error": str(e)}

# Mount PaaS API
app.include_router(paas_agent.router, prefix="/api/v1/paas", tags=["PaaS"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(login.router, prefix="/api/v1", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
app.include_router(tools.router, prefix="/api/v1", tags=["Tools"])
app.include_router(files.router, prefix="/api/v1", tags=["Files"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge"])
app.include_router(artifact.router, prefix="/api/v1/artifact", tags=["Artifact"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["Settings"])

# SKE Router
from server.ske.router import router as ske_router
app.include_router(ske_router, prefix="/api/v1/ske", tags=["SKE"])

# LangServe Routes (Legacy/Direct Graph Access)
add_routes(
    app,
    master_graph,
    path="/agent",
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# Static Files (Frontend)
static_root = (Path(__file__).resolve().parents[1] / "server" / "static").resolve()
if static_root.exists():
    app.mount("/static", StaticFiles(directory=str(static_root)), name="static_files")
    app.mount("/", StaticFiles(directory=str(static_root), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
