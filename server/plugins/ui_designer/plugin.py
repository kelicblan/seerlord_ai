from server.kernel.interface import AgentPlugin
from .graph import app

class UIDesignerPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "ui_designer"

    @property
    def name_zh(self) -> str:
        return "UI 设计师"

    @property
    def description(self) -> str:
        return "根据 UI 截图分析并生成 Vue 3 代码 (支持 MoE 模型)。"

    @property
    def enable_skills(self) -> bool:
        return True

    def get_graph(self):
        return app

plugin = UIDesignerPlugin()
