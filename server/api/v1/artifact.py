from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from server.core.database import get_db
from server.api.auth import get_current_tenant_id
from server.models.artifact import AgentArtifact

router = APIRouter()

_USER_FILES_BASE_DIR = (Path.cwd() / "server" / "data" / "user_files").resolve()
_LEGACY_ALLOWED_BASE_DIRS = [
    (Path.cwd() / "server" / "static" / "exports").resolve(),
    (Path.cwd() / "server" / "data" / "tutorial_exports").resolve(),
]


def _resolve_artifact_file_path(value: str) -> Path:
    raw = (value or "").strip()
    if not raw:
        raise HTTPException(status_code=404, detail="File not found on server")

    path = Path(raw)

    if path.is_absolute():
        resolved = path.resolve()
        allowed_bases = [_USER_FILES_BASE_DIR, *_LEGACY_ALLOWED_BASE_DIRS]
        for base in allowed_bases:
            try:
                resolved.relative_to(base)
                return resolved
            except Exception:
                continue
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    resolved = (_USER_FILES_BASE_DIR / path).resolve()
    try:
        resolved.relative_to(_USER_FILES_BASE_DIR)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    return resolved


class ArtifactSchema(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str]
    agent_id: str
    execution_id: Optional[str]
    type: str
    value: str
    title: Optional[str]
    description: Optional[str]
    total_tokens: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class ArtifactListResponse(BaseModel):
    items: List[ArtifactSchema]
    total: int

@router.get("/list", response_model=ArtifactListResponse)
async def list_artifacts(
    page: int = 1,
    page_size: int = 12,
    agent_id: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    # Count Query
    count_query = select(func.count()).where(AgentArtifact.tenant_id == tenant_id)
    if agent_id:
        count_query = count_query.where(AgentArtifact.agent_id == agent_id)
    
    total = await db.scalar(count_query) or 0

    # Data Query
    query = select(AgentArtifact).where(AgentArtifact.tenant_id == tenant_id)
    if agent_id:
        query = query.where(AgentArtifact.agent_id == agent_id)
    
    query = query.order_by(desc(AgentArtifact.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ArtifactListResponse(items=items, total=total)

@router.get("/{artifact_id}", response_model=ArtifactSchema)
async def get_artifact(
    artifact_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(AgentArtifact).where(
        AgentArtifact.id == artifact_id,
        AgentArtifact.tenant_id == tenant_id
    )
    result = await db.execute(query)
    artifact = result.scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact

class NoRangeFileResponse(FileResponse):
    """
    自定义 FileResponse，忽略 'Range' 请求头。
    强制返回 200 OK 和完整文件内容，防止返回 206 Partial Content。
    适用于前端使用 axios 下载文件且不处理分片的情况。
    """
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            # 过滤掉 Range 头
            scope["headers"] = [
                (k, v) for k, v in scope["headers"] 
                if k.lower() != b"range"
            ]
        await super().__call__(scope, receive, send)

@router.get("/{artifact_id}/preview")
async def preview_artifact(
    artifact_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(AgentArtifact).where(
        AgentArtifact.id == artifact_id,
        AgentArtifact.tenant_id == tenant_id
    )
    result = await db.execute(query)
    artifact = result.scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    if artifact.type == "content":
        return {"content": artifact.value, "type": "content"}
    elif artifact.type == "file":
        file_path = _resolve_artifact_file_path(artifact.value)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found on server")
        return {
            "type": "file",
            "filename": file_path.name,
            "download_url": f"/api/v1/artifact/{artifact_id}/download",
        }

@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(AgentArtifact).where(
        AgentArtifact.id == artifact_id,
        AgentArtifact.tenant_id == tenant_id
    )
    result = await db.execute(query)
    artifact = result.scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    if artifact.type == "file":
        file_path = _resolve_artifact_file_path(artifact.value)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found on server")
        
        media_type = "application/octet-stream"
        ext = file_path.suffix.lower()
        if ext in {".html", ".htm"}:
            media_type = "text/html; charset=utf-8"
        elif ext == ".pdf":
            media_type = "application/pdf"
        
        # 使用 NoRangeFileResponse 确保返回 200 OK
        return NoRangeFileResponse(path=str(file_path), filename=file_path.name, media_type=media_type)
    else:
        raise HTTPException(status_code=400, detail="Artifact is not a file")
    
    return {"type": "unknown", "value": artifact.value}
