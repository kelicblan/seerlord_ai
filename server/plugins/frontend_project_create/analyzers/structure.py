from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    id: str
    title: str
    module: str
    page_path: Optional[str] = None
    route_name: Optional[str] = None
    api_module: Optional[str] = None
    lld_source: Optional[str] = None
    source: Optional[str] = None


class PageDefinition(BaseModel):
    path: str
    route_name: str
    component: str
    module: str
    requirements: List[str] = Field(default_factory=list)


class RouteDefinition(BaseModel):
    path: str
    name: str
    component: str
    module: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class ApiModule(BaseModel):
    name: str
    module: str
    endpoints: List[str] = Field(default_factory=list)
    types_file: Optional[str] = None


class StoreDefinition(BaseModel):
    name: str
    module: str
    file_path: str


class TechStack(BaseModel):
    framework: str = "Vue 3.5+"
    build: str = "Vite 6.x"
    ui: str = "Element Plus"
    css: str = "Tailwind CSS 4.x"
    state: str = "Pinia 2.x"
    router: str = "Vue Router 4.x"
    utils: str = "@vueuse/core"

    def to_dict(self) -> Dict[str, str]:
        return {
            "framework": self.framework,
            "build": self.build,
            "ui": self.ui,
            "css": self.css,
            "state": self.state,
            "router": self.router,
            "utils": self.utils,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "TechStack":
        return cls(**data)


class DocumentSummary(BaseModel):
    requirements_count: int = 0
    pages_count: int = 0
    routes_count: int = 0
    api_modules_count: int = 0
    stores_count: int = 0
    business_domains: List[str] = Field(default_factory=list)


class BusinessDomain(BaseModel):
    name: str
    module: str
    pages: List[str] = Field(default_factory=list)
    api_modules: List[str] = Field(default_factory=list)
    stores: List[str] = Field(default_factory=list)


class CoverageMatrix(BaseModel):
    requirements: List[Requirement] = Field(default_factory=list)
    pages: List[PageDefinition] = Field(default_factory=list)
    routes: List[RouteDefinition] = Field(default_factory=list)
    api_modules: List[ApiModule] = Field(default_factory=list)
    stores: List[StoreDefinition] = Field(default_factory=list)

    def get_pages_by_module(self, module: str) -> List[PageDefinition]:
        return [p for p in self.pages if p.module == module]

    def get_routes_by_module(self, module: str) -> List[RouteDefinition]:
        return [r for r in self.routes if r.module == module]

    def get_api_modules_by_module(self, module: str) -> List[ApiModule]:
        return [a for a in self.api_modules if a.module == module]

    def get_requirements_by_module(self, module: str) -> List[Requirement]:
        return [r for r in self.requirements if r.module == module]

    def get_all_modules(self) -> List[str]:
        modules = set()
        modules.update(p.module for p in self.pages)
        modules.update(r.module for r in self.routes)
        modules.update(a.module for a in self.api_modules)
        modules.update(s.module for s in self.stores)
        return sorted(list(modules))
