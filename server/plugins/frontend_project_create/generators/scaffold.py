"""脚手架生成器：提供最小可运行的 Vue 3 项目基础文件。模板数据来自 _scaffold_data。"""
from ._scaffold_data import SCAFFOLD_FILES


class ScaffoldGenerator:
    """生成最小 Vue 3 + Vite + TypeScript + Element Plus + Tailwind CSS 脚手架。"""

    def generate_all(self) -> dict:
        """返回所有脚手架文件的路径与内容映射。"""
        return SCAFFOLD_FILES.copy()
