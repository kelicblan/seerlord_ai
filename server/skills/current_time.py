from datetime import datetime
import zoneinfo
from typing import Type, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# =============================================================================
# Input Schema Definition / 输入参数定义
# =============================================================================

class CurrentTimeInput(BaseModel):
    """
    Input schema for CurrentTimeSkill.
    Defines the arguments that the LLM needs to provide.
    
    CurrentTimeSkill 的输入模式。
    定义了 LLM 需要提供的参数。
    """
    timezone: str = Field(
        default="UTC",
        description="The timezone to get the current time for (e.g., 'UTC', 'America/New_York', 'Asia/Shanghai'). Defaults to UTC."
                    "\n获取当前时区的名称（例如 'UTC', 'America/New_York', 'Asia/Shanghai'）。默认为 UTC。"
    )

# =============================================================================
# Skill Definition / 技能定义
# =============================================================================

class CurrentTimeSkill(BaseTool):
    """
    A skill to get the current time in a specific timezone.
    Inherits from LangChain's BaseTool.
    
    一个用于获取特定时区当前时间的技能。
    继承自 LangChain 的 BaseTool。
    """
    
    # The unique name of the skill. The Router uses this to identify the skill.
    # 技能的唯一名称。Router 使用此名称来识别技能。
    name: str = "get_current_time"
    
    # A description of what the skill does. The LLM uses this to decide if it matches the user's intent.
    # 技能功能的描述。LLM 使用此描述来决定它是否符合用户的意图。
    description: str = "Get the current date and time for a specific timezone."
    
    # The argument schema class defined above.
    # 上面定义的参数模式类。
    args_schema: Type[BaseModel] = CurrentTimeInput

    def _run(self, timezone: str = "UTC") -> str:
        """
        The actual execution logic of the skill.
        技能的实际执行逻辑。
        
        Args:
            timezone (str): The timezone string.
            
        Returns:
            str: The formatted current time.
        """
        try:
            # Get the timezone object
            # 获取时区对象
            tz = zoneinfo.ZoneInfo(timezone)
            
            # Get current time in that timezone
            # 获取该时区的当前时间
            now = datetime.now(tz)
            
            # Format the output
            # 格式化输出
            return f"Current time in {timezone}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            
        except Exception as e:
            # Handle invalid timezones or other errors
            # 处理无效时区或其他错误
            return f"Error: Invalid timezone '{timezone}'. Please provide a valid IANA timezone name (e.g., 'Asia/Shanghai')."

# =============================================================================
# Registration / 注册
# =============================================================================

# Create an instance of the skill.
# The SkillRegistry scans for instances of BaseTool in this directory.
# 创建技能的一个实例。
# SkillRegistry 会扫描此目录中的 BaseTool 实例。
current_time = CurrentTimeSkill()
