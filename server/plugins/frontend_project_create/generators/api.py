from typing import Dict, List

from .base import BaseGenerator, GenerationResult, GenerationContext
from ._utils import normalize_module_name, normalize_type_name, normalize_file_path, should_normalize_module
from ..memory.short_term import ShortTermMemory


class ApiGenerator(BaseGenerator):
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
                
                api_file = f"src/api/{normalized_module}.ts"
                files[api_file] = self._generate_api_file(module, context)
            
            index_file = self._generate_api_index(modules)
            files["src/api/index.ts"] = index_file
            
            saved_files = self._save_files(files, context.project_path)
            
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

    def _generate_api_file(self, module: str, context: GenerationContext) -> str:
        # 规范化模块名
        normalized_module = normalize_module_name(module)
        normalized_type = normalize_type_name(module.title())
        
        lines = [
            f"import {{ request }} from './http'",
            f"import type {{ {normalized_type}Item, {normalized_type}ListParams, {normalized_type}ListResponse }} from '@/types/{normalized_module}'",
            f"import {{ mock{normalized_type}List }} from '@/mocks/{normalized_module}'",
            "",
            f"export const {normalized_module}Api = {{",
            "",
            f"  list: async (params: {normalized_type}ListParams) => {{",
            f"    // return request<{normalized_type}ListResponse>({{",
            f"    //   url: '/{module}/list',",
            f"    //   method: 'GET',",
            f"    //   params,",
            f"    // }})",
            f"    return mock{normalized_type}List(params)",
            "  },",
            "",
            f"  detail: async (id: string) => {{",
            f"    return request<{normalized_type}Item>({{",
            f"      url: '/{module}/detail/' + id,",
            f"      method: 'GET',",
            f"    }})",
            "  },",
            "",
            f"  create: async (data: Partial<{normalized_type}Item>) => {{",
            f"    return request<{normalized_type}Item>({{",
            f"      url: '/{module}/create',",
            f"      method: 'POST',",
            f"      data,",
            f"    }})",
            "  },",
            "",
            f"  update: async (id: string, data: Partial<{normalized_type}Item>) => {{",
            f"    return request<{normalized_type}Item>({{",
            f"      url: '/{module}/update/' + id,",
            f"      method: 'PUT',",
            f"      data,",
            f"    }})",
            "  },",
            "",
            f"  delete: async (id: string) => {{",
            f"    return request<void>({{",
            f"      url: '/{module}/delete/' + id,",
            f"      method: 'DELETE',",
            f"    }})",
            "  },",
            "};",
            "",
        ]
        
        return "\n".join(lines)

    def _generate_api_index(self, modules: List[str]) -> str:
        imports = [f"import {{ {normalize_module_name(m)}Api }} from './{normalize_module_name(m)}'" for m in modules]
        exports = [f"export {{ {normalize_module_name(m)}Api }}" for m in modules]
        
        lines = imports + [""] + exports
        
        return "\n".join(lines)
