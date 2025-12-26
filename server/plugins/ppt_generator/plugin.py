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
        return "分析 Markdown 内容并自动生成 PPT 演示文稿"

    def get_graph(self):
        return app

plugin = PPTGeneratorPlugin()
