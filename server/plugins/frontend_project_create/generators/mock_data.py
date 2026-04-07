from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import normalize_module_name, normalize_type_name
from ..memory.short_term import ShortTermMemory


class MockDataGenerator(BaseGenerator):
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
                
                mock_file = f"src/mocks/{normalized_module}.ts"
                files[mock_file] = self._generate_mock_file(module, context)
            
            saved_files = self._save_files(files, context.project_path)
            
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

    def _generate_mock_file(self, module: str, context: GenerationContext) -> str:
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())
        
        lines = [
            f"// {normalized_module} module mock data",
            "",
            f"export const {normalized_module}MockList = [",
            "  {",
            "    id: '1',",
            "    name: '示例数据 1',",
            "    createdAt: '2024-01-01 00:00:00',",
            "    updatedAt: '2024-01-01 00:00:00',",
            "  },",
            "  {",
            "    id: '2',",
            "    name: '示例数据 2',",
            "    createdAt: '2024-01-02 00:00:00',",
            "    updatedAt: '2024-01-02 00:00:00',",
            "  },",
            "];",
            "",
            f"export const {normalized_module}MockItem = {normalized_module}MockList[0];",
            "",
            f"export function mock{normalized_type}List(params?: any) {{",
            "  return Promise.resolve({",
            f"    code: 0,",
            f"    message: 'success',",
            f"    data: {{",
            f"      list: {normalized_module}MockList,",
            f"      total: {normalized_module}MockList.length,",
            "      page: 1,",
            "      pageSize: 10,",
            f"    }}",
            "  });",
            "}",
            "",
        ]
        
        return "\n".join(lines)
