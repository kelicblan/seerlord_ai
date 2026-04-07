from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import normalize_module_name, normalize_type_name
from ..memory.short_term import ShortTermMemory


class TypeGenerator(BaseGenerator):
    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        try:
            files = {}
            
            modules = context.coverage_matrix.get_all_modules()
            for module in modules:
                # 规范化模块名（移除连字符）
                normalized_module = normalize_module_name(module)
                normalized_type = normalize_type_name(module.title())
                
                type_file = f"src/types/{normalized_module}.ts"
                files[type_file] = self._generate_type_file(module, context)
            
            saved_files = self._save_files(files, context.project_path)
            
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

    def _generate_type_file(self, module: str, context: GenerationContext) -> str:
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())
        
        pages = context.coverage_matrix.get_pages_by_module(module)
        apis = context.coverage_matrix.get_api_modules_by_module(module)
        
        lines = [
            f"// {normalized_module} module types",
            "",
            "// API types",
            f"export interface {normalized_type}ListParams {{",
            "  page?: number",
            "  pageSize?: number",
            "  keyword?: string",
            "}",
            "",
            f"export interface {normalized_type}Item {{",
            "  id: string",
            "  createdAt?: string",
            "  updatedAt?: string",
            "}",
            "",
            f"export interface {normalized_type}ListResponse {{",
            f"  list: {normalized_type}Item[]",
            "  total: number",
            "  page: number",
            "  pageSize: number",
            "}",
            "",
        ]
        
        return "\n".join(lines)
