from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.plugins._skill_evolver_.graph import app

class SkillEvolverPlugin(AgentPlugin):
    """
    Skill Evolver System Agent.
    Responsible for analyzing conversations and creating new skills.
    """
    @property
    def name(self) -> str:
        return "_skill_evolver_"

    @property
    def name_zh(self) -> str:
        return "技能进化器"

    @property
    def description(self) -> str:
        return "System agent responsible for analyzing conversation gaps and evolving new skills."

    def get_graph(self) -> Runnable:
        return app

    def get_critique_instructions(self) -> str:
        return "Ensure the generated skill definition is valid and complete."

# Export the plugin instance
plugin = SkillEvolverPlugin()

def get_agent():
    return app
