from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.plugins._mail_service_.graph import app

class MailServicePlugin(AgentPlugin):
    """
    Mail Service System Agent.
    Responsible for sending emails to application agents.
    """
    @property
    def name(self) -> str:
        return "_mail_service_"

    @property
    def name_zh(self) -> str:
        return "邮件服务"

    @property
    def description(self) -> str:
        return "System agent responsible for sending emails to application agents based on their configuration."

    @property
    def enable_skills(self) -> bool:
        return False

    def get_graph(self) -> Runnable:
        return app

    def get_critique_instructions(self) -> str:
        return "Ensure the email was sent to the correct recipient with the correct content."

# Export the plugin instance
plugin = MailServicePlugin()

def get_agent():
    return app
