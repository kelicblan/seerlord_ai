from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from server.core.database import get_db
from server.api.v1.login import get_current_user
from server.models.user import User
from server.crud import chat as crud_chat

router = APIRouter()

class ChatSessionResponse(BaseModel):
    id: str
    title: Optional[str]
    agent_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    role: str
    content: Optional[str] = ""
    thoughts: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sessions = await crud_chat.get_sessions_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return sessions

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify session belongs to user
    session = await crud_chat.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
    messages = await crud_chat.get_messages_by_session(db, session_id)
    return messages

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await crud_chat.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}
