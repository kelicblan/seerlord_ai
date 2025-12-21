from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.plugins._voyager_agent_.graph import app

class VoyagerPlugin(AgentPlugin):
    """
    Voyager Agent Plugin.
    Implements autonomous skill learning and execution.
    """
    
    @property
    def name(self) -> str:
        return "_voyager_agent_"

    @property
    def name_zh(self) -> str:
        return "探索者 (Voyager)"

    @property
    def description(self) -> str:
        return (
            "An autonomous agent that can learn new skills, write code, and execute complex tasks. "
            "Use this for: "
            "1. Requests requiring code generation or execution. "
            "2. Complex learning plans that involve creating interactive content or tools. "
            "3. Tasks where the agent needs to 'learn' how to do something first. "
            "4. General purpose complex problem solving."
        )

    def get_graph(self) -> Runnable:
        return app

    def get_critique_instructions(self) -> str:
        return (
            "- Ensure the generated code or skill is correct and executable.\n"
            "- If a new skill was evolved, verify it solves the user's specific problem.\n"
            "- Check if the explanation is clear and the code output is presented properly."
        )

# Export the plugin instance for the registry to find
plugin = VoyagerPlugin()

def get_agent():
    return app
