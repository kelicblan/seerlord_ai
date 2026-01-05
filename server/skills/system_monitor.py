from typing import Type, Optional
import psutil
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# =============================================================================
# Input Schema Definition / 输入参数定义
# =============================================================================

class SystemMonitorInput(BaseModel):
    """
    Input schema for SystemMonitorSkill.
    
    SystemMonitorSkill 的输入模式。
    """
    resource_type: str = Field(
        default="all",
        description="The type of resource to monitor. Options: 'cpu', 'memory', 'disk', 'all'. Defaults to 'all'."
                    "\n要监控的资源类型。选项：'cpu', 'memory', 'disk', 'all'。默认为 'all'。"
    )

# =============================================================================
# Skill Definition / 技能定义
# =============================================================================

class SystemMonitorSkill(BaseTool):
    """
    A skill to monitor system resources (CPU, Memory, Disk).
    
    一个用于监控系统资源（CPU、内存、磁盘）的技能。
    """
    
    name: str = "get_system_status"
    description: str = "Get current system resource usage including CPU, Memory, and Disk."
    args_schema: Type[BaseModel] = SystemMonitorInput

    def _run(self, resource_type: str = "all") -> str:
        """
        Execute the system monitoring logic.
        执行系统监控逻辑。
        
        Args:
            resource_type (str): Type of resource to check.
            
        Returns:
            str: Formatted system status report.
        """
        try:
            report = []
            
            # CPU Info
            if resource_type in ["cpu", "all"]:
                cpu_percent = psutil.cpu_percent(interval=1)
                report.append(f"CPU Usage: {cpu_percent}%")
            
            # Memory Info
            if resource_type in ["memory", "all"]:
                mem = psutil.virtual_memory()
                total_gb = round(mem.total / (1024**3), 2)
                used_gb = round(mem.used / (1024**3), 2)
                report.append(f"Memory: {used_gb}GB / {total_gb}GB ({mem.percent}%)")
            
            # Disk Info
            if resource_type in ["disk", "all"]:
                disk = psutil.disk_usage('/')
                total_disk_gb = round(disk.total / (1024**3), 2)
                used_disk_gb = round(disk.used / (1024**3), 2)
                report.append(f"Disk Usage: {used_disk_gb}GB / {total_disk_gb}GB ({disk.percent}%)")
                
            return " | ".join(report)
            
        except Exception as e:
            return f"Error monitoring system: {str(e)}"

# =============================================================================
# Registration / 注册
# =============================================================================

# Create instance to be picked up by SkillRegistry
# 创建实例以便 SkillRegistry 扫描
system_monitor = SystemMonitorSkill()
