from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from .graph import fta_graph

class FTAPlugin(AgentPlugin):
    """
    FTA (故障树分析) 专家插件。
    负责对事故或事件进行递归的根原因分析。
    """

    @property
    def name(self) -> str:
        return "fta_analyst"

    @property
    def description(self) -> str:
        return "Analyzes accidents using Fault Tree Analysis (FTA) to find root causes recursively."

    def get_graph(self) -> Runnable:
        return fta_graph

    def get_critique_instructions(self) -> str:
        return (
            "- Output must contain at least 2 levels of causes if applicable.\n"
            "- Logic gates (AND/OR) must be clearly specified.\n"
            "- 'basic_event' must be a true root cause, not an abstract concept."
        )
