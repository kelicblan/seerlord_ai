from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, func

from server.core.database import get_db
from server.models.user import User
from server.schemas.user import UserCreate, UserUpdate, UserResponse, UserPage
from server.core.security import get_password_hash
from server.api.v1.login import get_current_user
from loguru import logger

router = APIRouter()

# Dependency to check if user is superuser
async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    校验当前用户是否为超级用户。
    输入：
    - current_user：已登录用户
    输出：
    - User：超级用户对象
    """
    logger.debug(f"校验超级用户：username={current_user.username} is_superuser={current_user.is_superuser}")
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/", response_model=UserPage)
async def read_users(
    page: int = 1,
    size: int = 10,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Retrieve users with pagination. Only for superusers.
    """
    logger.debug(f"读取用户列表：page={page} size={size} search={search}")
    
    # Base query
    query = select(User)
    if search:
        logger.debug(f"应用搜索过滤：search={search}")
        query = query.where(User.username.ilike(f"%{search}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Pagination
    skip = (page - 1) * size
    result = await db.execute(query.offset(skip).limit(size))
    users = result.scalars().all()
    
    return UserPage(items=users, total=total or 0, page=page, size=size)

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Create new user. Only for superusers.
    """
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Update a user. Only for superusers.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
        
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        password = update_data.pop("password")
        user.hashed_password = get_password_hash(password)
        
    for field, value in update_data.items():
        setattr(user, field, value)
        
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Delete a user. Only for superusers.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    if user.id == current_user.id:
         raise HTTPException(
            status_code=400,
            detail="Users cannot delete themselves",
        )
        
    await db.delete(user)
    await db.commit()
    return user
