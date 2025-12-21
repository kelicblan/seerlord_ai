from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.config_engine.builder import AgentBuilder
import os

class FTAPlugin(AgentPlugin):
    """
    FTA (故障树分析) 专家插件。
    负责对事故或事件进行递归的根原因分析。
    (Migrated to YAML-based Configuration)
    """
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "fta_analyst"

    @property
    def name_zh(self) -> str:
        return "故障树分析专家"

    @property
    def description(self) -> str:
        return "Analyzes accidents using Fault Tree Analysis (FTA) to find root causes recursively."

    def get_graph(self) -> Runnable:
        if not self._graph:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.yaml")
            # We use the same file for agents and tasks for simplicity in this migration, 
            # or we could split them. Here I put both in config.yaml.
            # AgentBuilder expects separate paths, so we pass the same file twice 
            # if the YAML contains both 'agents' and 'tasks' keys (Loader handles this).
            builder = AgentBuilder(agents_path=config_path, tasks_path=config_path)
            self._graph = builder.build()
        return self._graph

    def get_critique_instructions(self) -> str:
        return (
            "- Output must contain at least 2 levels of causes if applicable.\n"
            "- Logic gates (AND/OR) must be clearly specified.\n"
            "- 'basic_event' must be a true root cause, not an abstract concept."
        )

# Export the plugin instance
plugin = FTAPlugin()

