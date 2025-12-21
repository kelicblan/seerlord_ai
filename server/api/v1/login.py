from datetime import timedelta
from typing import Annotated
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from jose import jwt, JWTError
from pydantic import BaseModel, Field

from server.core import security
from server.core.config import settings
from server.core.database import get_db
from server.models.user import User
from loguru import logger

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    username: str
    is_active: bool
    is_superuser: bool

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Authenticate user
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]):
    """
    获取当前登录用户。
    输入：
    - token：Bearer Token
    - db：数据库会话
    输出：
    - User：当前用户对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token 解析失败：username 为空")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"Token 解析失败：{e}")
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        logger.warning(f"用户不存在：{username}")
        raise credentials_exception
    return user

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get current user.
    """
    return current_user

class SetupRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)

@router.post("/setup/initialize")
async def setup_initialize(
    payload: SetupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    setup_token: Annotated[str | None, Header(alias="X-Setup-Token")] = None,
):
    """
    首启初始化：当用户表为空时，创建第一个管理员账号。
    安全策略：
    - 必须配置环境变量 `SETUP_TOKEN` 才启用
    - 请求头需要携带 `X-Setup-Token` 且匹配
    - 仅当用户表为空时允许执行一次
    """
    if not settings.SETUP_TOKEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setup endpoint disabled")

    if not setup_token or not secrets.compare_digest(setup_token, settings.SETUP_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid setup token")

    result = await db.execute(select(func.count(User.id)))
    user_count = int(result.scalar() or 0)
    if user_count > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Setup already completed")

    logger.info(f"首启初始化：创建管理员用户 username={payload.username}")

    new_user = User(
        username=payload.username,
        hashed_password=security.get_password_hash(payload.password),
        is_active=True,
        is_superuser=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "initialized",
        "user": {"id": new_user.id, "username": new_user.username, "is_superuser": new_user.is_superuser},
    }
