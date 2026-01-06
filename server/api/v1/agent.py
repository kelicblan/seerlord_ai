from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import json
import asyncio
import yaml
from loguru import logger
from langchain_core.load.dump import dumpd
from langgraph.graph import START, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from server.kernel.registry import registry
from server.kernel.master_graph import build_master_graph
from server.api.auth import get_current_tenant_id, get_current_tenant_id_optional
from server.core.database import get_db, SessionLocal
from server.core.config import settings
from server.models.user import User
from server.models.llm_trace import LLMTrace
from server.models.tutorial_export import TutorialExport
from server.memory.manager import MemoryManager
from server.crud import chat as crud_chat
from datetime import datetime
from pathlib import Path

router = APIRouter()

# Helper to load config values
def load_plugin_config_values(plugin_id: str) -> Dict[str, Any]:
    try:
        plugin_dir = Path(settings.PLUGIN_DIR)
        dir_name = registry.get_plugin_dir(plugin_id) or plugin_id
        config_path = plugin_dir / dir_name / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # We are interested in 'configurable' section
                return data.get("configurable", {})
    except Exception as e:
        logger.error(f"Failed to load config for {plugin_id}: {e}")
    return {}

# Optional Auth Dependency
async def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
        
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    return user

class StreamInput(BaseModel):
    input: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None
    version: str = "v2"

@router.post("/stream_events")
async def stream_events(
    request: StreamInput,
    tenant_id: str = Depends(get_current_tenant_id_optional),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_info_str = f" (User: {current_user.username})" if current_user else " (No User Token)"
    logger.info(f"Stream events request from {tenant_id}{user_info_str}")
    
    input_data = request.input
    config = request.config or {}
    
    # Inject User Context
    if current_user:
        user_id = str(current_user.id)
        # 1. Inject into Input (for Graph State)
        input_data["user_id"] = user_id
        input_data["tenant_id"] = tenant_id # Ensure tenant_id is also in input
        
        # 2. Inject into Config (for Checkpointers)
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["user_id"] = user_id
        config["configurable"]["tenant_id"] = tenant_id
    else:
        # Fallback: Ensure tenant_id is passed
        input_data["tenant_id"] = tenant_id
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["tenant_id"] = tenant_id
        
        # FIX: Ensure user_id is passed even if not authenticated
        # Trust input provided user_id or fall back to default
        user_id = input_data.get("user_id", "default_user")
        input_data["user_id"] = user_id
        config["configurable"]["user_id"] = user_id
        
        if "metadata" not in config:
            config["metadata"] = {}
        config["metadata"]["tenant_id"] = tenant_id
    
    # Extract query from messages (Common for Memory and History)
    msgs = input_data.get("messages", [])
    query = ""
    if isinstance(msgs, list) and msgs:
        # Find last human message
        for m in reversed(msgs):
            if isinstance(m, dict) and m.get("type") == "human":
                query = m.get("content", "")
                break
            elif hasattr(m, "type") and m.type == "human":
                query = m.content
                break

    # [Middleware] Memory Loading (Pre-Execution)
    # Check config for memory settings. Default enabled=True unless explicitly disabled.
    memory_config = config.get("configurable", {}).get("memory", {})
    memory_enabled = memory_config.get("enabled", True)

    if memory_enabled:
        try:
            mem_mgr = await MemoryManager.get_instance()
            
            if query:
                user_id_for_mem = input_data.get("user_id", "default_user")
                context_result = await mem_mgr.retrieve_context(query=query, user_id=user_id_for_mem)
                
                # Format context
                parts = []
                if context_result.get("profile"):
                    parts.append("### User Profile:")
                    parts.extend([f"- {p}" for p in context_result["profile"]])
                if context_result.get("memories"):
                    parts.append("\n### Relevant Past Events:")
                    parts.extend([f"- {m}" for m in context_result["memories"]])
                
                memory_context = "\n".join(parts)
                input_data["memory_context"] = memory_context
                logger.info(f"Memory injected for user {user_id_for_mem}")
        except Exception as e:
            logger.error(f"Memory loading failed: {e}")

    logger.info(f"Received Input: {input_data}")
    logger.info(f"Received Config: {config}")

    # Check plugin target
    target_plugin = input_data.get("target_plugin")
    
    app = None
    if target_plugin and target_plugin != "auto":
        plugin = registry.get_plugin(target_plugin)
        if plugin:
            # Load static config from disk
            disk_config = load_plugin_config_values(target_plugin)
            if disk_config:
                if "configurable" not in config:
                    config["configurable"] = {}
                # Merge: Runtime overrides disk if key exists (standard behavior), 
                # but here runtime is likely empty for these keys, so disk fills them.
                for k, v in disk_config.items():
                    if k not in config["configurable"]:
                        config["configurable"][k] = v
            
            logger.info(f"Targeting plugin directly: {target_plugin}")
            app = plugin.get_graph()
        else:
            logger.warning(f"Plugin {target_plugin} not found, using Master Graph")
            
    if not app:
        # Build master graph
        # Note: In production, we might want to cache this or use a singleton
        # But build_master_graph() compiles the graph, so we should probably reuse it if possible.
        # For now, let's call it.
        app = build_master_graph()
    
    # [Middleware Fix] Inject Language Instruction for Direct Plugin Execution
    # When routing manually to a plugin (not 'auto'), the Master Graph logic is skipped.
    # We must inject the language preference into the messages manually.
    if target_plugin and target_plugin != "auto":
        language = input_data.get("language", "zh-CN")
        lang_instruction = ""
        if language == "en":
            lang_instruction = "IMPORTANT: respond in English."
        elif language == "zh-TW":
            lang_instruction = "IMPORTANT: respond in Traditional Chinese (繁体中文)."
        else:
            lang_instruction = "IMPORTANT: respond in Simplified Chinese (简体中文)."
            
        # Prepend SystemMessage to messages list in input_data
        if "messages" in input_data:
            from langchain_core.messages import SystemMessage
            # Convert dicts to objects if needed, but usually we just add a dict if input is raw dicts
            # LangGraph usually handles dicts with 'type' key if using add_messages
            # But let's check what format input_data['messages'] is in. 
            # It comes from Pydantic StreamInput.input which is Dict[str, Any].
            # Usually messages is a list of dicts: [{'type': 'human', 'content': '...'}]
            
            msgs = input_data["messages"]
            if isinstance(msgs, list):
                # Insert at the beginning
                msgs.insert(0, {"type": "system", "content": lang_instruction})
    
    async def event_generator():
        # Track active runs for tracing
        active_traces = {} # run_id -> trace_dict
        final_ai_response = "" # Track final response for memory
        collected_thoughts = [] # Track thoughts for history

        # [History] Save User Message
        thread_id = config.get("configurable", {}).get("thread_id")
        if current_user and thread_id and query:
             try:
                async with SessionLocal() as session:
                    # Ensure session exists
                    chat_session = await crud_chat.get_or_create_session(
                        session, 
                        session_id=thread_id, 
                        user_id=current_user.id,
                        agent_id=target_plugin or "master"
                    )
                    
                    await crud_chat.create_message(
                        session,
                        session_id=thread_id,
                        role="user",
                        content=query
                    )
             except Exception as e:
                logger.error(f"Failed to save user message to history: {e}")
        
        try:
            # LangGraph astream_events yields events
            # We need to map them to SSE format
            
            async for event in app.astream_events(input_data, config=config, version="v2"):
                # Serialize event to JSON
                try:
                    # Use dumpd to convert LangChain objects to serializable dicts
                    serializable_event = dumpd(event)
                    data = json.dumps(serializable_event)
                    yield f"data: {data}\n\n"
                    
                    # Log event type for debugging
                    event_type = serializable_event.get("event")
                    
                    # Collect thoughts for UI history
                    if event_type in ["on_tool_start", "on_tool_end", "on_chain_start", "on_chain_end", "on_chat_model_start", "on_chat_model_end"]:
                         collected_thoughts.append(serializable_event)

                    if event_type == "on_chat_model_start":
                        logger.info(f"Stream: Chat Model Start (RunID: {serializable_event.get('run_id')})")
                    elif event_type == "on_chat_model_stream":
                        # Too verbose to log every chunk, but useful for deep debug
                        pass 
                    elif event_type == "on_chat_model_end":
                        logger.info(f"Stream: Chat Model End (RunID: {serializable_event.get('run_id')})")
                        # Capture output for memory
                        try:
                            data_payload = serializable_event.get("data", {})
                            output = data_payload.get("output", {})
                            if isinstance(output, dict) and output.get("content"):
                                final_ai_response = output.get("content")
                        except:
                            pass
                    elif event_type == "on_tool_start":
                        logger.info(f"Stream: Tool Start (Name: {serializable_event.get('name')})")
                    elif event_type == "on_tool_end":
                        logger.info(f"Stream: Tool End (Name: {serializable_event.get('name')})")
                    
                    # --- DB Tracing Logic ---
                    try:
                        event_type = serializable_event.get("event")
                        run_id = serializable_event.get("run_id")
                        
                        if event_type == "on_chat_model_start":
                            data_payload = serializable_event.get("data", {})
                            inp = data_payload.get("input", {})
                            prompts_list = inp.get("messages", [])
                            if not prompts_list:
                                prompts_list = inp.get("prompts", [])
                                
                            active_traces[run_id] = {
                                "run_id": run_id,
                                "session_id": config.get("configurable", {}).get("thread_id"),
                                "tenant_id": tenant_id,
                                "user_id": str(current_user.id) if current_user else None,
                                "model_name": serializable_event.get("name"),
                                "prompts": dumpd(prompts_list),
                                "start_time": datetime.now(),
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "total_tokens": 0
                            }
                            
                        elif event_type == "on_chat_model_end":
                            trace_data = active_traces.pop(run_id, None)
                            if trace_data:
                                data_payload = serializable_event.get("data", {})
                                output = data_payload.get("output", {})
                                
                                # Try to extract usage metadata
                                usage = None
                                if output.get("usage_metadata"):
                                    usage = output["usage_metadata"]
                                elif output.get("response_metadata", {}).get("token_usage"):
                                    u = output["response_metadata"]["token_usage"]
                                    usage = {
                                        "input_tokens": u.get("prompt_tokens", 0),
                                        "output_tokens": u.get("completion_tokens", 0),
                                        "total_tokens": u.get("total_tokens", 0)
                                    }
                                
                                if usage:
                                    trace_data["input_tokens"] = usage.get("input_tokens", 0)
                                    trace_data["output_tokens"] = usage.get("output_tokens", 0)
                                    trace_data["total_tokens"] = usage.get("total_tokens", 0)
                                
                                trace_data["outputs"] = dumpd(output)
                                trace_data["end_time"] = datetime.now()
                                
                                # Save to DB asynchronously
                                async with SessionLocal() as session:
                                    try:
                                        db_trace = LLMTrace(**trace_data)
                                        session.add(db_trace)
                                        await session.commit()
                                    except Exception as db_err:
                                        logger.error(f"Failed to save LLM trace: {db_err}")
                                        
                    except Exception as trace_err:
                        # Don't break stream for tracing errors
                        logger.warning(f"Error in tracing logic: {trace_err}")
                    # ------------------------

                except Exception as json_err:
                    logger.error(f"Failed to serialize event: {json_err}")
            
            # [Middleware] Memory Saving (Post-Execution)
            memory_auto_save = memory_config.get("auto_save", True)
            memory_read_only = memory_config.get("read_only", False)
            
            # [History] Save AI Message
            if current_user and thread_id and final_ai_response:
                try:
                    async with SessionLocal() as session:
                        await crud_chat.create_message(
                            session,
                            session_id=thread_id,
                            role="ai",
                            content=final_ai_response,
                            thoughts=collected_thoughts
                        )
                except Exception as e:
                    logger.error(f"Failed to save AI message to history: {e}")

            # We need query variable from outer scope
            # Ensure final_ai_response is not empty
            if memory_enabled and memory_auto_save and not memory_read_only and final_ai_response and query:
                try:
                    # Re-get instance to be safe (though it's singleton)
                    mem_mgr = await MemoryManager.get_instance()
                    await mem_mgr.add_interaction(
                        user_input=query,
                        ai_response=final_ai_response,
                        user_id=input_data.get("user_id", "default_user"),
                        metadata={
                            "tenant_id": tenant_id,
                            "source": target_plugin or "master_graph"
                        }
                    )
                    logger.info("Interaction saved to memory.")
                except Exception as mem_err:
                    logger.error(f"Failed to save memory: {mem_err}")
                    
        except Exception as e:
            logger.error(f"Error in stream_events: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/master/graph")
async def get_master_graph():
    """Get Mermaid graph definition for Master Graph"""
    try:
        graph = build_master_graph()
        mermaid = graph.get_graph().draw_mermaid()
        return {"mermaid": mermaid}
    except Exception as e:
        logger.error(f"Failed to generate master graph: {e}")
        return {"mermaid": None, "error": str(e)}

@router.get("/{plugin_id}/graph/json")
async def get_plugin_graph_json(
    plugin_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get JSON graph definition for a plugin or master graph"""
    try:
        app = None
        if plugin_id == "master":
            app = build_master_graph()
        else:
            plugin = registry.get_plugin(plugin_id)
            if not plugin:
                raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
            app = plugin.get_graph()
            
        graph = app.get_graph()
        
        # Convert to JSON serializable format
        nodes = []
        for node_id, node in graph.nodes.items():
            nodes.append({
                "id": node.id,
                "type": "custom" if node.id not in [START, END] else "input" if node.id == START else "output",
                "data": {
                    "label": node.id,
                    "metadata": str(node.data) if hasattr(node, "data") else ""
                }
            })
            
        edges = []
        for edge in graph.edges:
            edges.append({
                "id": f"{edge.source}-{edge.target}",
                "source": edge.source,
                "target": edge.target,
                "type": "smoothstep"
            })
            
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        logger.error(f"Failed to generate graph JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tutorial_exports/{export_id}/download")
async def download_tutorial_export(
    export_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TutorialExport).where(TutorialExport.id == export_id))
    export = result.scalars().first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if export.tenant_id and export.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if export.user_id:
        if not current_user or export.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden")

    user_files_base_dir = (Path.cwd() / "server" / "data" / "user_files").resolve()
    legacy_base_dir = (Path.cwd() / "server" / "data" / "tutorial_exports").resolve()

    raw_path = (export.file_path or "").strip()
    if not raw_path:
        raise HTTPException(status_code=404, detail="Export file missing")

    # Handle S3/Remote URLs
    if raw_path.startswith("http://") or raw_path.startswith("https://"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=raw_path)

    p = Path(raw_path)
    if p.is_absolute():
        file_path = p.resolve()
        allowed_bases = [user_files_base_dir, legacy_base_dir]
        for base in allowed_bases:
            try:
                file_path.relative_to(base)
                break
            except Exception:
                continue
        else:
            raise HTTPException(status_code=400, detail="Invalid export path")
    else:
        safe_user_id = "".join(ch for ch in (export.user_id or "") if ch.isalnum() or ch in {"-", "_"})
        expected_base = (user_files_base_dir / safe_user_id).resolve() if safe_user_id else user_files_base_dir
        file_path = (user_files_base_dir / p).resolve()
        try:
            file_path.relative_to(expected_base)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid export path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export file missing")

    return FileResponse(
        path=str(file_path),
        media_type="text/html; charset=utf-8",
        filename=f"tutorial_{export_id}.html"
    )
