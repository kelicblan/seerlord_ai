import sys
import asyncio
import os

# Fix for Windows and psycopg (must be done before any async loop starts)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from loguru import logger
import uvicorn

from server.core.config import settings
from server.kernel.registry import registry
from server.kernel.master_graph import build_master_graph
from server.kernel.mcp_manager import mcp_manager
from server.kernel.memory_manager import memory_manager

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
    Handle application startup and shutdown events.
    Specifically manages the database connection pool and MCP servers.
    """
    logger.info("Starting SeerLord AI Kernel...")
    
    # 1. Database Connection Management
    if settings.DATABASE_URL:
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
        logger.warning("No DATABASE_URL found. System running with In-Memory persistence.")
    
    # 2. Initialize MCP Manager
    mcp_config_path = "mcp.json"
    if os.path.exists(mcp_config_path):
        logger.info(f"Initializing MCP Manager from {mcp_config_path}...")
        await mcp_manager.load_config(mcp_config_path)
    else:
        logger.info("No mcp.json found, skipping MCP initialization.")

    # 3. Initialize Memory Manager (Long-term Memory)
    logger.info("Initializing Memory Manager...")
    await memory_manager.initialize()

    yield
    
    # Cleanup
    logger.info("Shutting down SeerLord AI Kernel...")
    
    # 1. Close Memory Manager
    await memory_manager.close()
    
    # 2. Close MCP connections
    await mcp_manager.close_all()
    
    # 3. Close Database Pool
    if hasattr(app.state, "db_pool"):
        logger.info("Closing Database Connection Pool...")
        await app.state.db_pool.close()

app = FastAPI(
    title="SeerLord AI Kernel",
    version="1.0.0",
    description="Micro-kernel Agent Platform with LangGraph",
    lifespan=lifespan
)

# -----------------------------------------------------------------------------
# Middleware & Exception Handlers
# -----------------------------------------------------------------------------
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Global Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

# -----------------------------------------------------------------------------
# LangServe Routes
# -----------------------------------------------------------------------------
def per_req_config_modifier(config: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """
    Modify configuration per request.
    Injects default thread_id for playground if missing.
    """
    config = config.copy()
    configurable = config.get("configurable", {})
    if "thread_id" not in configurable:
        configurable["thread_id"] = "default_playground_thread"
        config["configurable"] = configurable
    return config

add_routes(
    app,
    master_graph,
    path="/api/v1/agent",
    playground_type="default",
    per_req_config_modifier=per_req_config_modifier,
)

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/v1/plugins")
async def get_plugins():
    """
    Get list of loaded plugins.
    """
    return [
        {"id": name, "name": p.name, "description": p.description}
        for name, p in registry.plugins.items()
    ]

@app.get("/api/v1/mcp/status")
async def get_mcp_status():
    """
    Get the status of MCP servers.
    """
    return mcp_manager.get_status_summary()

@app.get("/api/v1/agent/{plugin_id}/graph")
async def get_agent_graph(plugin_id: str):
    """
    Get the Mermaid graph definition for a specific agent plugin.
    Use 'master' as plugin_id to get the main workflow graph.
    """
    if plugin_id == "master":
        try:
            mermaid_syntax = master_graph.get_graph().draw_mermaid()
            return {"mermaid": mermaid_syntax}
        except Exception as e:
            logger.error(f"Failed to generate master graph: {e}")
            return {"error": str(e)}

    plugin = registry.plugins.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    try:
        compiled_graph = plugin.get_graph()
        mermaid_syntax = compiled_graph.get_graph().draw_mermaid()
        return {"mermaid": mermaid_syntax}
    except Exception as e:
        logger.error(f"Failed to generate graph for {plugin_id}: {e}")
        return {"error": str(e)}

@app.get("/api/v1/agent/execution_log/{thread_id}")
async def get_execution_log(thread_id: str):
    """
    Get execution history (state snapshots) for a specific thread.
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        # Note: master_graph is a CompiledGraph
        # Use async iterator for AsyncPostgresSaver
        history = []
        async for snapshot in master_graph.aget_state_history(config):
            history.append({
                "values": snapshot.values,
                "next": list(snapshot.next) if snapshot.next else [],
                "config": snapshot.config,
                "metadata": snapshot.metadata,
                "created_at": snapshot.created_at,
                "parent_config": snapshot.parent_config
            })
             
        return history
    except Exception as e:
        logger.error(f"Failed to get execution log for {thread_id}: {e}")
        return {"error": str(e)}

# -----------------------------------------------------------------------------
# Static Files & Frontend
# -----------------------------------------------------------------------------
# Mount static files
app.mount("/static", StaticFiles(directory="server/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("server/static/index.html")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config():
    return {}

# Fix for Playground path issues (LangServe Frontend Bug Fix)
@app.post("/api/v1/agent/playground/{path:path}")
async def proxy_playground_api(path: str, request: Request):
    target_url = f"/api/v1/agent/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    return RedirectResponse(url=target_url, status_code=307)

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
