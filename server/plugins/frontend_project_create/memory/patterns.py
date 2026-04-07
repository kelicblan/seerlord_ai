from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FilePattern(BaseModel):
    name: str
    file_type: str
    module: str
    template: str
    dependencies: List[str] = Field(default_factory=list)


class ModulePattern(BaseModel):
    name: str
    module: str
    files: List[FilePattern] = Field(default_factory=list)
    generation_order: List[str] = Field(default_factory=list)


class VueFilePatterns:
    PAGE_PATTERNS = {
        "list": "views/{domain}/{name}/list/{Name}List.vue",
        "detail": "views/{domain}/{name}/detail/{Name}Detail.vue",
        "form": "views/{domain}/{name}/form/{Name}Form.vue",
        "create": "views/{domain}/{name}/create/{Name}Create.vue",
        "edit": "views/{domain}/{name}/edit/{Name}Edit.vue",
    }
    
    COMPONENT_PATTERNS = {
        "table": "components/{domain}/{name}/{Name}Table.vue",
        "form": "components/{domain}/{name}/{Name}Form.vue",
        "filter": "components/{domain}/{name}/{Name}Filter.vue",
        "dialog": "components/{domain}/{name}/{Name}Dialog.vue",
    }


class TypeScriptPatterns:
    API_PATTERN = "src/api/{module}.ts"
    STORE_PATTERN = "src/stores/{module}.ts"
    COMPOSABLE_PATTERN = "src/composables/use{Module}.ts"
    TYPE_PATTERN = "src/types/{module}.ts"
    MOCK_PATTERN = "src/mocks/{module}.ts"


class PatternLibrary:
    def __init__(self):
        self.vue_patterns = VueFilePatterns()
        self.ts_patterns = TypeScriptPatterns()
        self._custom_patterns: Dict[str, str] = {}

    def get_file_pattern(self, category: str, name: str, **kwargs) -> Optional[str]:
        if category == "page" and name in self.vue_patterns.PAGE_PATTERNS:
            return self.vue_patterns.PAGE_PATTERNS[name].format(**kwargs)
        elif category == "component" and name in self.vue_patterns.COMPONENT_PATTERNS:
            return self.vue_patterns.COMPONENT_PATTERNS[name].format(**kwargs)
        elif category == "api":
            return self.ts_patterns.API_PATTERN.format(**kwargs)
        elif category == "store":
            return self.ts_patterns.STORE_PATTERN.format(**kwargs)
        elif category == "composable":
            return self.ts_patterns.COMPOSABLE_PATTERN.format(**kwargs)
        elif category == "type":
            return self.ts_patterns.TYPE_PATTERN.format(**kwargs)
        elif category == "mock":
            return self.ts_patterns.MOCK_PATTERN.format(**kwargs)
        elif category in self._custom_patterns:
            return self._custom_patterns[category].format(**kwargs)
        return None

    def add_custom_pattern(self, name: str, pattern: str) -> None:
        self._custom_patterns[name] = pattern

    def get_module_pattern(self, module_name: str) -> ModulePattern:
        files = []
        
        files.append(FilePattern(
            name=f"{module_name}Api",
            file_type="api",
            module=module_name,
            template=self.ts_patterns.API_PATTERN.format(module=module_name),
            dependencies=[],
        ))
        
        files.append(FilePattern(
            name=f"{module_name}Store",
            file_type="store",
            module=module_name,
            template=self.ts_patterns.STORE_PATTERN.format(module=module_name),
            dependencies=[f"{module_name}Api"],
        ))
        
        files.append(FilePattern(
            name=f"use{module_name.title().replace('_', '')}",
            file_type="composable",
            module=module_name,
            template=self.ts_patterns.COMPOSABLE_PATTERN.format(module=module_name.title()),
            dependencies=[f"{module_name}Store"],
        ))
        
        return ModulePattern(
            name=module_name,
            module=module_name,
            files=files,
            generation_order=["api", "store", "composable", "page"],
        )


pattern_library = PatternLibrary()
