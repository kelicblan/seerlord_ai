from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from .graph import app
import os

class NewsReporterPlugin(AgentPlugin):
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "news_reporter"

    @property
    def name_zh(self) -> str:
        return "私人情报官"

    @property
    def description(self) -> str:
        return "Fetches real-time tech news from NewsMinimalist, translates, and emails a briefing."

    @property
    def enable_skills(self) -> bool:
        return True

    def get_graph(self) -> Runnable:
        return app

    def get_critique_instructions(self) -> str:
        return (
            "- Must cite at least 3 distinct sources.\n"
            "- Tone must be objective and journalistic.\n"
            "- Summary must cover key 'Who, What, When, Where, Why' elements."
        )

# Export the plugin instance
plugin = NewsReporterPlugin()
