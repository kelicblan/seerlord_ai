from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.config_engine.builder import AgentBuilder
import os

class NewsReporterPlugin(AgentPlugin):
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "news_reporter"

    @property
    def name_zh(self) -> str:
        return "新闻资讯"

    @property
    def description(self) -> str:
        return "Searches and summarizes global major news from the last 24 hours."

    def get_graph(self) -> Runnable:
        if not self._graph:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.yaml")
            builder = AgentBuilder(agents_path=config_path, tasks_path=config_path)
            self._graph = builder.build()
        return self._graph

    def get_critique_instructions(self) -> str:
        return (
            "- Must cite at least 3 distinct sources.\n"
            "- Tone must be objective and journalistic.\n"
            "- Summary must cover key 'Who, What, When, Where, Why' elements."
        )

# Export the plugin instance
plugin = NewsReporterPlugin()
