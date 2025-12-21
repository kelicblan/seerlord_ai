from abc import ABC, abstractmethod
from langchain_core.runnables import Runnable

class AgentPlugin(ABC):
    """
    代理插件的抽象基类。
    所有具体的插件都必须继承此类并实现必要的方法。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        插件的唯一标识符（ID）。
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        插件的描述。
        路由器（Router）将使用此描述来理解插件的功能并进行选择。
        """
        pass

    @property
    def name_zh(self) -> str:
        """
        [可选] 插件的中文名称，用于前端展示。
        如果未实现，前端可能会回退显示 ID (name)。
        """
        return ""

    @abstractmethod
    def get_graph(self) -> Runnable:
        """
        返回插件编译后的 LangGraph 图（CompiledGraph）。
        """
        pass

    def get_critique_instructions(self) -> str:
        """
        [可选] 返回针对该插件的特定 Critic 指令。
        默认返回空字符串（即使用通用标准）。
        """
        return ""
