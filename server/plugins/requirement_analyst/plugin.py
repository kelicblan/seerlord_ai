from server.kernel.interface import AgentPlugin
from .graph import app

class RequirementAnalystPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "requirement_analyst"

    @property
    def name_zh(self) -> str:
        return "用户需求分析"

    @property
    def description(self) -> str:
        return "上传需求文档，自动生成《项目需求规格说明书》和《系统开发指导手册》"

    def get_graph(self):
        return app

plugin = RequirementAnalystPlugin()
