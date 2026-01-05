from langchain_core.runnables import Runnable
from server.kernel.interface import AgentPlugin
from .graph import app as comic_graph

class ComicBookPlugin(AgentPlugin):
    """
    漫画式学习课程插件。
    负责根据用户需求生成漫画风格的 PDF 图书。
    """
    def __init__(self):
        self._graph = None

    @property
    def name(self) -> str:
        return "comic_book_generator"

    @property
    def name_zh(self) -> str:
        return "漫画式学习课程"

    @property
    def description(self) -> str:
        return "Creates comic book style educational content in PDF format. Transforms complex topics into engaging visual stories."

    @property
    def enable_skills(self) -> bool:
        return True

    def get_graph(self) -> Runnable:
        if not self._graph:
            self._graph = comic_graph
        return self._graph

# Export the plugin instance
plugin = ComicBookPlugin()
