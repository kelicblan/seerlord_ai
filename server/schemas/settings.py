from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional, List, Union

class LLMModelBase(BaseModel):
    name: str
    provider: str
    base_url: Optional[str] = None
    model_name: str
    api_key: Optional[str] = None
    model_type: str = "llm"
    price_per_1k_tokens: Optional[float] = 0.0

class LLMModelCreate(LLMModelBase):
    pass

class LLMModelUpdate(LLMModelBase):
    pass

class LLMModelResponse(LLMModelBase):
    id: int
    created_at: Optional[Union[str, datetime]] = None

    @field_validator("created_at", mode="before")
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True

class SystemSettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SystemSettingCreate(SystemSettingBase):
    pass

class SystemSettingResponse(SystemSettingBase):
    class Config:
        from_attributes = True
