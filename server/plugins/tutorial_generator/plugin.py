from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.config_engine.builder import AgentBuilder
from .graph import app as tutorial_graph
import os

class TutorialPlugin(AgentPlugin):
    """
    教程生成器插件。
    负责根据用户需求生成结构化的学习计划和教程大纲。
    """
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "tutorial_generator"

    @property
    def name_zh(self) -> str:
        return "首席学习顾问"

    @property
    def description(self) -> str:
        return "Generates comprehensive learning plans, tutorials, and structured educational content. Use this for any request related to learning a new skill, language, or subject."

    def get_graph(self) -> Runnable:
        if not self._graph:
            # Switch to custom Python Graph definition to support Skill System
            self._graph = tutorial_graph
        return self._graph

    def get_critique_instructions(self) -> str:
        return (
            "- Plan must be broken down into clear steps or modules.\n"
            "- Learning goals for each module must be specific.\n"
            "- Must include estimated time for each section."
        )

    @property
    def enable_skills(self) -> bool:
        return True

# Export the plugin instance
plugin = TutorialPlugin()

