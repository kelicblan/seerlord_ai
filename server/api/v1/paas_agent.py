from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger
import yaml
import asyncio
import os
from pathlib import Path

from server.api.auth import get_current_tenant_id
from server.config_engine.builder import AgentBuilder
from server.config_engine.loader import AgentConfig, TaskConfig
from server.core.config import settings
from server.kernel.registry import registry

router = APIRouter()

# --- Request/Response Models ---

class AgentDef(BaseModel):
    agents: Dict[str, AgentConfig]
    tasks: List[TaskConfig]

class ExecutionRequest(BaseModel):
    config: AgentDef
    inputs: Optional[Dict[str, Any]] = None

class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    message: str

class ConfigUpdateRequest(BaseModel):
    content: str  # YAML content string

# --- Endpoints ---

@router.get("/agents/{agent_id}/config")
async def get_agent_config(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get the configuration (config.yaml) for a specific agent.
    """
    # Security check: prevent path traversal
    if ".." in agent_id or "/" in agent_id or "\\" in agent_id:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    plugin_dir = Path(settings.PLUGIN_DIR)
    
    # Resolve directory from registry if possible
    dir_name = registry.get_plugin_dir(agent_id)
    if dir_name:
        config_path = plugin_dir / dir_name / "config.yaml"
    else:
        # Fallback to agent_id as directory name
        config_path = plugin_dir / agent_id / "config.yaml"

    if not config_path.exists():
        # Check if it's a python-only agent or config is missing
        raise HTTPException(status_code=404, detail="Configuration file not found for this agent")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        logger.error(f"Failed to read config for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")

@router.post("/agents/{agent_id}/config")
async def update_agent_config(
    agent_id: str,
    request: ConfigUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Update the configuration (config.yaml) for a specific agent.
    """
    # Security check
    if ".." in agent_id or "/" in agent_id or "\\" in agent_id:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    plugin_dir = Path(settings.PLUGIN_DIR)
    
    # Resolve directory from registry if possible
    dir_name = registry.get_plugin_dir(agent_id)
    if dir_name:
        config_path = plugin_dir / dir_name / "config.yaml"
    else:
        # Fallback to agent_id as directory name
        config_path = plugin_dir / agent_id / "config.yaml"

    if not config_path.exists():
         raise HTTPException(status_code=404, detail="Configuration file not found for this agent")
    
    # Validate YAML format
    try:
        yaml.safe_load(request.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        
        logger.info(f"Agent {agent_id} config updated by tenant {tenant_id}")
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update config for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")

@router.post("/execute", response_model=ExecutionResponse)
async def execute_agent_config(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Dynamically build and execute an Agent workflow based on the provided configuration.
    This is the core PaaS endpoint.
    """
    logger.info(f"Received execution request from Tenant: {tenant_id}")
    
    execution_id = f"exec-{tenant_id}-{asyncio.get_event_loop().time()}"
    
    # In a real system, we would:
    # 1. Validate the config deeply.
    # 2. Spin up a dedicated worker or asyncio task.
    # 3. Store the status in DB.
    
    # For now, we will run it in background and log (Proof of Concept)
    background_tasks.add_task(
        run_dynamic_agent, 
        request.config, 
        request.inputs or {}, 
        tenant_id,
        execution_id
    )
    
    return ExecutionResponse(
        execution_id=execution_id,
        status="accepted",
        message="Agent workflow execution started in background."
    )

async def run_dynamic_agent(config: AgentDef, inputs: Dict[str, Any], tenant_id: str, execution_id: str):
    logger.info(f"🚀 [ExecID: {execution_id}] Starting Dynamic Agent for {tenant_id}")
    
    try:
        # 1. Save temp config files (Builder currently reads from disk)
        # Optimization: Refactor Builder to accept Dict directly.
        # For now, we hack it by writing temp files.
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            agents_path = os.path.join(tmpdirname, "agents.yaml")
            tasks_path = os.path.join(tmpdirname, "tasks.yaml")
            
            # Convert Pydantic models back to dict for YAML dump
            agents_dict = {"agents": {k: v.dict() for k, v in config.agents.items()}}
            tasks_dict = {"tasks": [t.dict() for t in config.tasks]}
            
            with open(agents_path, 'w', encoding='utf-8') as f:
                yaml.dump(agents_dict, f)
            with open(tasks_path, 'w', encoding='utf-8') as f:
                yaml.dump(tasks_dict, f)
                
            # 2. Build Graph
            builder = AgentBuilder(agents_path, tasks_path)
            app = builder.build()
            
            # 3. Execute
            initial_state = {"results": {}} # inputs can be merged here
            
            async for event in app.astream(initial_state):
                 for key, value in event.items():
                    logger.info(f"✅ [ExecID: {execution_id}] Step Completed: {key}")
                    # In a real system, we would push this event to SSE / Webhook
            
            logger.info(f"🎉 [ExecID: {execution_id}] Workflow Finished Successfully.")
            
    except Exception as e:
        logger.error(f"❌ [ExecID: {execution_id}] Execution Failed: {e}")
