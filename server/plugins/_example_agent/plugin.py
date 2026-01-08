from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.config_engine.builder import AgentBuilder
import os

class ExampleAgentPlugin(AgentPlugin):
    """
    Example Agent Plugin Definition.
    示例 Agent 插件定义。
    """
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        """
        Agent unique name.
        Agent 唯一名称。
        """
        return "_example_agent"

    @property
    def name_zh(self) -> str:
        """
        Agent Chinese name.
        Agent 中文名称。
        """
        return "示例助手"

    @property
    def description(self) -> str:
        """
        Agent description.
        Agent 描述。
        """
        return "Conducts in-depth research on a topic, executing multiple search steps and generating a comprehensive report."

    @property
    def enable_skills(self) -> bool:
        """
        Enable skills for this agent.
        为该 agent 启用技能。
        """
        return True

    def get_graph(self) -> Runnable:
        """
        Build and return the agent execution graph.
        构建并返回 agent 执行图。
        """
        if not self._graph:
            # We import here to avoid circular dependencies if any
            from .graph import app
            self._graph = app
        return self._graph

    def get_critique_instructions(self) -> str:
        """
        Instructions for the critique loop.
        批评循环的说明。
        """
        return (
            "Review the research report for depth, accuracy, and structure. "
            "Ensure all claims are supported by the collected information. "
            "The report should be comprehensive and well-organized."
        )

# Export the plugin instance
# 导出插件实例
plugin = ExampleAgentPlugin()
