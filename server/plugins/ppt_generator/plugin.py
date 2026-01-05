from server.kernel.interface import AgentPlugin
from .graph import app

class PPTGeneratorPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "ppt_generator"

    @property
    def name_zh(self) -> str:
        return "自动生成PPT"

    @property
    def description(self) -> str:
        return "Generates PowerPoint (PPTX) presentations from a topic or outline."

    @property
    def enable_skills(self) -> bool:
        return True

    def get_graph(self):
        return app

plugin = PPTGeneratorPlugin()
