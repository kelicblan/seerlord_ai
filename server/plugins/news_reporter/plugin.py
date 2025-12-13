from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.plugins.news_reporter.graph import graph

class NewsReporterPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "news_reporter"

    @property
    def description(self) -> str:
        return "Searches and summarizes global major news from the last 24 hours."

    def get_graph(self) -> Runnable:
        return graph

    def get_critique_instructions(self) -> str:
        return (
            "- Must cite at least 3 distinct sources.\n"
            "- Tone must be objective and journalistic.\n"
            "- Summary must cover key 'Who, What, When, Where, Why' elements."
        )

# Export the plugin instance
plugin = NewsReporterPlugin()
