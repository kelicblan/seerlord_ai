from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from .graph import app

class PrivateButlerPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "private_butler"

    @property
    def name_zh(self) -> str:
        return "私人管家"

    @property
    def description(self) -> str:
        return "A proactive private butler that manages memory (PKG), tasks, and daily briefings."

    @property
    def enable_skills(self) -> bool:
        return True

    def get_graph(self) -> Runnable:
        return app
    
    def get_critique_instructions(self) -> str:
        return (
            "- Ensure memory operations are confirmed.\n"
            "- Proactive briefings should be concise and polite.\n"
        )

# Export the plugin instance
plugin = PrivateButlerPlugin()
