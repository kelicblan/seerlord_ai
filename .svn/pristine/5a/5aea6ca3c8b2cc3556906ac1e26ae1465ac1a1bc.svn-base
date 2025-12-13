from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from .graph import tutorial_graph

class TutorialPlugin(AgentPlugin):
    """
    教程生成器插件。
    负责根据用户需求生成结构化的学习计划和教程大纲。
    """

    @property
    def name(self) -> str:
        return "tutorial_agent"

    @property
    def description(self) -> str:
        return "Generates structured learning plans and tutorials based on user requests."

    def get_graph(self) -> Runnable:
        return tutorial_graph

    def get_critique_instructions(self) -> str:
        return (
            "- Plan must be broken down into clear steps or modules.\n"
            "- Learning goals for each module must be specific.\n"
            "- Must include estimated time for each section."
        )
