"""业务组件生成器：为每个业务模块生成通用 Vue 组件。模板数据来自 _component_data。"""
from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._component_data import COMPONENT_TEMPLATES
from ..memory.short_term import ShortTermMemory
from ..analyzers.structure import PageDefinition


class ComponentGenerator(BaseGenerator):
    """为每个业务模块生成通用组件（Table、FormModal、SearchBar、DeleteConfirm）及页面级表单组件。"""

    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        """为 coverage_matrix 中的每个模块生成通用组件和页面级表单组件。"""
        try:
            files: Dict[str, str] = {}
            pages = context.coverage_matrix.pages
            modules = context.coverage_matrix.get_all_modules()

            for module in modules:
                module_pages = [p for p in pages if p.module == module]
                files.update(self._generate_module_components(module, module_pages))

            saved_files = self._save_files(files, context.project_path)

            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

    def _generate_module_components(
        self,
        module: str,
        pages: List[PageDefinition],
    ) -> Dict[str, str]:
        """为单个模块生成 Table、FormModal、SearchBar、DeleteConfirm，以及每个页面的表单组件。"""
        files: Dict[str, str] = {}
        module_title = module.title()

        files[f"src/components/{module}/Table.vue"] = self._render_table(module, module_title)
        files[f"src/components/{module}/FormModal.vue"] = self._render_form_modal(module, module_title)
        files[f"src/components/{module}/SearchBar.vue"] = self._render_search_bar()
        files[f"src/components/{module}/DeleteConfirm.vue"] = self._render_delete_confirm()

        for page in pages:
            path_parts = page.path.strip("/").split("/")
            component_name = "".join(
                p.title().replace("-", "")
                for p in path_parts
                if p and not p.startswith(":")
            )
            form_file = f"src/components/{module}/{component_name}Form.vue"
            files[form_file] = self._render_page_form(component_name)

        return files

    def _render_table(self, module: str, module_title: str) -> str:
        content = COMPONENT_TEMPLATES["table"]
        content = content.replace("{module}", module)
        content = content.replace("{module_title}", module_title)
        return content

    def _render_form_modal(self, module: str, module_title: str) -> str:
        content = COMPONENT_TEMPLATES["form_modal"]
        content = content.replace("{module}", module)
        content = content.replace("{module_title}", module_title)
        return content

    def _render_search_bar(self) -> str:
        return COMPONENT_TEMPLATES["search_bar"]

    def _render_delete_confirm(self) -> str:
        return COMPONENT_TEMPLATES["delete_confirm"]

    def _render_page_form(self, page_name: str) -> str:
        content = COMPONENT_TEMPLATES["page_form"]
        content = content.replace("{page_name}", page_name)
        return content
