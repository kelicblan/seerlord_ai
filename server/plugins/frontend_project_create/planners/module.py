from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from ..analyzers.structure import PageDefinition, ApiModule, StoreDefinition


class FileType(str):
    TYPE_DEFINITION = "type_definition"
    MOCK_DATA = "mock_data"
    API_LAYER = "api_layer"
    COMPOSABLE = "composable"
    STORE = "store"
    PAGE = "page"
    COMPONENT = "component"
    ROUTE = "route"


class FilePlan(BaseModel):
    file_type: str
    file_path: str
    module: str
    dependencies: List[str] = Field(default_factory=list)
    page: Optional[PageDefinition] = None
    api_module: Optional[ApiModule] = None
    store: Optional[StoreDefinition] = None
    priority: int = 0


class GenerationPhase:
    TYPES = 1
    MOCK_DATA = 2
    API_LAYER = 3
    COMPOSABLES = 4
    STORES = 5
    PAGES = 6
    COMPONENTS = 7
    ROUTES = 8


class ModulePlanner:
    def __init__(
        self,
        module: str,
        pages: List[PageDefinition],
        api_modules: List[ApiModule],
        stores: List[StoreDefinition],
    ):
        self.module = module
        self.pages = pages
        self.api_modules = api_modules
        self.stores = stores

    def plan_files(self) -> List[FilePlan]:
        plans = []
        
        plans.extend(self._plan_type_files())
        plans.extend(self._plan_mock_data_files())
        plans.extend(self._plan_api_files())
        plans.extend(self._plan_store_files())
        plans.extend(self._plan_composable_files())
        plans.extend(self._plan_page_files())
        plans.extend(self._plan_component_files())
        
        return plans

    def plan_execution_order(self, files: List[FilePlan]) -> List[FilePlan]:
        sorted_files = []
        
        type_files = [f for f in files if f.file_type == FileType.TYPE_DEFINITION]
        mock_files = [f for f in files if f.file_type == FileType.MOCK_DATA]
        api_files = [f for f in files if f.file_type == FileType.API_LAYER]
        store_files = [f for f in files if f.file_type == FileType.STORE]
        composable_files = [f for f in files if f.file_type == FileType.COMPOSABLE]
        page_files = [f for f in files if f.file_type == FileType.PAGE]
        component_files = [f for f in files if f.file_type == FileType.COMPONENT]
        
        sorted_files.extend(sorted(type_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(mock_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(api_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(store_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(composable_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(component_files, key=lambda f: f.priority))
        sorted_files.extend(sorted(page_files, key=lambda f: f.priority))
        
        return sorted_files

    def _plan_type_files(self) -> List[FilePlan]:
        plans = []
        
        plans.append(FilePlan(
            file_type=FileType.TYPE_DEFINITION,
            file_path=f"src/types/{self.module}.ts",
            module=self.module,
            dependencies=[],
            priority=GenerationPhase.TYPES,
        ))
        
        for api in self.api_modules:
            if api.types_file:
                plans.append(FilePlan(
                    file_type=FileType.TYPE_DEFINITION,
                    file_path=api.types_file,
                    module=self.module,
                    dependencies=[],
                    priority=GenerationPhase.TYPES,
                    api_module=api,
                ))
        
        return plans

    def _plan_mock_data_files(self) -> List[FilePlan]:
        plans = []
        
        plans.append(FilePlan(
            file_type=FileType.MOCK_DATA,
            file_path=f"src/mocks/{self.module}.ts",
            module=self.module,
            dependencies=[f"src/types/{self.module}.ts"],
            priority=GenerationPhase.MOCK_DATA,
        ))
        
        return plans

    def _plan_api_files(self) -> List[FilePlan]:
        plans = []
        
        for api in self.api_modules:
            plans.append(FilePlan(
                file_type=FileType.API_LAYER,
                file_path=f"src/api/{api.name}.ts",
                module=self.module,
                dependencies=[
                    f"src/types/{self.module}.ts",
                    f"src/mocks/{self.module}.ts",
                ],
                priority=GenerationPhase.API_LAYER,
                api_module=api,
            ))
        
        return plans

    def _plan_store_files(self) -> List[FilePlan]:
        plans = []
        
        for store in self.stores:
            plans.append(FilePlan(
                file_type=FileType.STORE,
                file_path=store.file_path,
                module=self.module,
                dependencies=[
                    f"src/api/{self.module}.ts",
                ],
                priority=GenerationPhase.STORES,
                store=store,
            ))
        
        return plans

    def _plan_composable_files(self) -> List[FilePlan]:
        plans = []
        
        plans.append(FilePlan(
            file_type=FileType.COMPOSABLE,
            file_path=f"src/composables/use{self.module.title()}.ts",
            module=self.module,
            dependencies=[
                f"src/stores/{self.module}.ts",
            ],
            priority=GenerationPhase.COMPOSABLES,
        ))
        
        return plans

    def _plan_page_files(self) -> List[FilePlan]:
        plans = []
        
        for i, page in enumerate(self.pages):
            path_parts = page.path.strip("/").split("/")
            view_name = "".join(p.title().replace("-", "") for p in path_parts if p and not p.startswith(":"))
            view_file = f"src/views/{page.path.strip('/')}/{view_name}.vue"
            
            plans.append(FilePlan(
                file_type=FileType.PAGE,
                file_path=view_file,
                module=self.module,
                dependencies=[
                    f"src/composables/use{self.module.title()}.ts",
                ],
                priority=GenerationPhase.PAGES + i,
                page=page,
            ))
        
        return plans

    def _plan_component_files(self) -> List[FilePlan]:
        plans = []

        common_components = [
            ("Table", "数据表格组件，支持排序、分页、筛选"),
            ("FormModal", "表单弹窗组件，封装新增/编辑逻辑"),
            ("SearchBar", "搜索栏组件，统一查询体验"),
            ("DeleteConfirm", "删除确认对话框"),
        ]

        for name, desc in common_components:
            component_file = f"src/components/{self.module}/{name}.vue"
            plans.append(FilePlan(
                file_type=FileType.COMPONENT,
                file_path=component_file,
                module=self.module,
                dependencies=[
                    f"src/types/{self.module}.ts",
                    f"src/composables/use{self.module.title()}.ts",
                ],
                priority=GenerationPhase.COMPONENTS,
            ))

        for page in self.pages:
            path_parts = page.path.strip("/").split("/")
            component_name = "".join(p.title().replace("-", "") for p in path_parts if p and not p.startswith(":"))

            forms = [
                (f"{component_name}Form", "新增/编辑表单组件"),
            ]
            for form_name, form_desc in forms:
                form_file = f"src/components/{self.module}/{form_name}.vue"
                plans.append(FilePlan(
                    file_type=FileType.COMPONENT,
                    file_path=form_file,
                    module=self.module,
                    dependencies=[
                        f"src/types/{self.module}.ts",
                        f"src/composables/use{self.module.title()}.ts",
                    ],
                    priority=GenerationPhase.COMPONENTS + 1,
                    page=page,
                ))

        return plans
