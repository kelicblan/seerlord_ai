from server.kernel.interface import AgentPlugin
from server.kernel.adk import ADK

config = ADK.load_config(__file__)


class FrontendProjectCreatePlugin(AgentPlugin):
    """frontend_project_create 的插件入口。"""

    @property
    def name(self) -> str:
        return config.info.get("name", "frontend-project-create")

    @property
    def name_zh(self) -> str:
        return config.info.get("name_zh", "前端项目创建")

    @property
    def description(self) -> str:
        return config.info.get("description", "")

    @property
    def enable_skills(self) -> bool:
        return config.is_feature_enabled("skills")

    def get_graph(self):
        from .graph import app

        return app


agent_plugin = FrontendProjectCreatePlugin()
