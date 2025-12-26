from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import uuid

from server.core.database import get_db
from server.models.user import User
from server.models.api_key import ApiKey
from server.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from server.api.v1.login import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all API keys for the current user.
    """
    query = select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(
    key_in: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new API key.
    """
    # Generate a random key
    raw_key = f"sk-{secrets.token_hex(16)}"
    
    new_key = ApiKey(
        user_id=current_user.id,
        key=raw_key,
        name=key_in.name,
        is_active=key_in.is_active
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return new_key

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an API key.
    """
    query = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    result = await db.execute(query)
    key_obj = result.scalars().first()
    
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    await db.delete(key_obj)
    await db.commit()

@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: str,
    key_in: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update API key (e.g., rename or toggle active).
    """
    query = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    result = await db.execute(query)
    key_obj = result.scalars().first()
    
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key not found")
    
    if key_in.name is not None:
        key_obj.name = key_in.name
    if key_in.is_active is not None:
        key_obj.is_active = key_in.is_active
        
    db.add(key_obj)
    await db.commit()
    await db.refresh(key_obj)
    return key_obj
