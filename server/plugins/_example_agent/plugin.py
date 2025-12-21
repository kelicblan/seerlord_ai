from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.config_engine.builder import AgentBuilder
import os

class ExampleAgentPlugin(AgentPlugin):
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "_example_agent"

    @property
    def name_zh(self) -> str:
        return "示例助手"

    @property
    def description(self) -> str:
        return "Conducts in-depth research on a topic, executing multiple search steps and generating a comprehensive report."

    def get_graph(self) -> Runnable:
        if not self._graph:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.yaml")
            builder = AgentBuilder(agents_path=config_path, tasks_path=config_path)
            self._graph = builder.build()
        return self._graph

    def get_critique_instructions(self) -> str:
        return (
            "Review the research report for depth, accuracy, and structure. "
            "Ensure all claims are supported by the collected information. "
            "The report should be comprehensive and well-organized."
        )

# Export the plugin instance
plugin = ExampleAgentPlugin()
