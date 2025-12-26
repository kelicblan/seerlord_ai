from pydantic import BaseModel, Field

class GeneratePPTInput(BaseModel):
    md_content: str = Field(description="用于生成 PPT 的 Markdown 内容")
    user_id: str | None = Field(default=None, description="登录用户ID（用于落盘目录隔离）")
