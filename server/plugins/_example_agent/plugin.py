from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from server.plugins._example_agent.graph import graph

class ExampleAgentPlugin(AgentPlugin):
    @property
    def name(self) -> str:
        return "research_assistant"

    @property
    def description(self) -> str:
        return "Conducts in-depth research on a topic, executing multiple search steps and generating a comprehensive report."

    def get_graph(self) -> Runnable:
        return graph

    def get_critique_instructions(self) -> str:
        return (
            "Review the research report for depth, accuracy, and structure. "
            "Ensure all claims are supported by the collected information. "
            "The report should be comprehensive and well-organized."
        )

# Export the plugin instance
plugin = ExampleAgentPlugin()
