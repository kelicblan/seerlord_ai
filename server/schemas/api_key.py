from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApiKeyBase(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = True

class ApiKeyCreate(ApiKeyBase):
    name: str

class ApiKeyUpdate(ApiKeyBase):
    pass

class ApiKeyResponse(ApiKeyBase):
    id: str
    key: str # Show full key (or masked if preferred, but for new creation we show full)
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
