from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class UserPage(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
