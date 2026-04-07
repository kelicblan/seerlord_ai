import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from .structure import (
    CoverageMatrix,
    Requirement,
    PageDefinition,
    RouteDefinition,
    ApiModule,
    StoreDefinition,
    TechStack,
    DocumentSummary,
    BusinessDomain,
)


class DocumentAnalyzer:
    def __init__(self, doc_content: str):
        self.doc_content = doc_content
        self.lines = doc_content.split("\n")

    def parse_coverage_matrix(self) -> CoverageMatrix:
        coverage_matrix = CoverageMatrix()
        
        requirements = self._parse_requirements_section()
        coverage_matrix.requirements = requirements
        
        pages = self._parse_pages_from_requirements(requirements)
        coverage_matrix.pages = pages
        
        routes = self._parse_routes_from_pages(pages)
        coverage_matrix.routes = routes
        
        api_modules = self._parse_api_modules_from_requirements(requirements)
        coverage_matrix.api_modules = api_modules
        
        stores = self._parse_stores_from_modules(coverage_matrix.get_all_modules())
        coverage_matrix.stores = stores
        
        return coverage_matrix

    def extract_tech_stack(self) -> TechStack:
        tech_stack = TechStack()
        
        vue_match = re.search(r"Vue\s*3\.?\d*", self.doc_content, re.IGNORECASE)
        if vue_match:
            tech_stack.framework = vue_match.group(0)
        
        vite_match = re.search(r"Vite\s*\d+\.?\d*", self.doc_content, re.IGNORECASE)
        if vite_match:
            tech_stack.build = vite_match.group(0)
        
        element_match = re.search(r"Element\s*Plus", self.doc_content, re.IGNORECASE)
        if element_match:
            tech_stack.ui = element_match.group(0)
        
        tailwind_match = re.search(r"Tailwind\s*CSS\s*\d+\.?\d*", self.doc_content, re.IGNORECASE)
        if tailwind_match:
            tech_stack.css = tailwind_match.group(0)
        
        pinia_match = re.search(r"Pinia\s*\d+\.?\d*", self.doc_content, re.IGNORECASE)
        if pinia_match:
            tech_stack.state = pinia_match.group(0)
        
        router_match = re.search(r"Vue\s*Router\s*\d+\.?\d*", self.doc_content, re.IGNORECASE)
        if router_match:
            tech_stack.router = router_match.group(0)
        
        vueuse_match = re.search(r"@vueuse/core", self.doc_content, re.IGNORECASE)
        if vueuse_match:
            tech_stack.utils = vueuse_match.group(0)
        
        return tech_stack

    def extract_business_domains(self) -> List[BusinessDomain]:
        domains = []
        modules = self._extract_modules_from_matrix()
        
        for module in modules:
            domain = BusinessDomain(
                name=module,
                module=module,
                pages=[],
                api_modules=[],
                stores=[],
            )
            domains.append(domain)
        
        return domains

    def generate_summary(self) -> DocumentSummary:
        coverage = self.parse_coverage_matrix()
        modules = coverage.get_all_modules()
        
        return DocumentSummary(
            requirements_count=len(coverage.requirements),
            pages_count=len(coverage.pages),
            routes_count=len(coverage.routes),
            api_modules_count=len(coverage.api_modules),
            stores_count=len(coverage.stores),
            business_domains=modules,
        )

    def _parse_requirements_section(self) -> List[Requirement]:
        requirements = []
        
        table_pattern = re.compile(
            r"\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|"
        )
        
        in_matrix = False
        for line in self.lines:
            if "功能需求覆盖矩阵" in line or "REQ-FUN-" in line:
                in_matrix = True
            
            if in_matrix and table_pattern.match(line):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 6 and "REQ-FUN-" in parts[0]:
                    req_id = parts[0]
                    title = parts[1]
                    module = self._extract_module_name(parts[2])
                    page_path = self._extract_page_path(parts[3])
                    route_name = self._extract_route_name(parts[4])
                    api_module = self._extract_api_module(parts[5])
                    lld_source = parts[6] if len(parts) > 6 else None
                    source = parts[7] if len(parts) > 7 else None
                    
                    requirements.append(Requirement(
                        id=req_id,
                        title=title,
                        module=module,
                        page_path=page_path,
                        route_name=route_name,
                        api_module=api_module,
                        lld_source=lld_source,
                        source=source,
                    ))
        
        return requirements

    def _parse_pages_from_requirements(self, requirements: List[Requirement]) -> List[PageDefinition]:
        pages = []
        seen_paths = set()
        
        for req in requirements:
            if req.page_path and req.page_path not in seen_paths:
                component = self._path_to_component(req.page_path)
                pages.append(PageDefinition(
                    path=req.page_path,
                    route_name=req.route_name or self._path_to_route_name(req.page_path),
                    component=component,
                    module=req.module,
                    requirements=[req.id],
                ))
                seen_paths.add(req.page_path)
            elif req.page_path:
                for page in pages:
                    if page.path == req.page_path:
                        page.requirements.append(req.id)
                        break
        
        extra_pages = self._parse_extra_pages()
        for page_def in extra_pages:
            if page_def.path not in seen_paths:
                pages.append(page_def)
                seen_paths.add(page_def.path)
        
        return pages

    def _parse_extra_pages(self) -> List[PageDefinition]:
        """从文档中其他位置解析额外的页面，如路由表格、页面列表等。
        
        优化：只使用严格的路由正则匹配，避免硬编码模块名导致误解析。
        """
        extra_pages = []
        seen_paths = set()
        
        # 使用严格的路由正则匹配，避免误解析
        route_table_pattern = re.compile(
            r"[/\\]?([a-zA-Z][a-zA-Z0-9_-]*)[/\\]([a-zA-Z][a-zA-Z0-9_-]*)\.vue",
            re.IGNORECASE
        )
        
        # Vue Router 路径匹配
        vue_router_pattern = re.compile(
            r"(?:path|route)[:\s]*['\"](/(?:[a-zA-Z][a-zA-Z0-9_-]*/?)*)['\"]",
            re.IGNORECASE
        )
        
        for line in self.lines:
            line_clean = line.strip()
            
            # 匹配路由表格
            if route_table_pattern.search(line_clean):
                match = route_table_pattern.search(line_clean)
                module = match.group(1).lower()
                page_name = match.group(2)
                path = f"/{module}/{page_name.lower()}"
                
                if path not in seen_paths:
                    seen_paths.add(path)
                    extra_pages.append(PageDefinition(
                        path=path,
                        route_name=page_name.replace("-", " ").replace("_", " ").title(),
                        component=f"{module.title()}{page_name.title()}",
                        module=module,
                        requirements=[],
                    ))
            
            # 匹配 Vue Router 路径
            vue_match = vue_router_pattern.search(line_clean)
            if vue_match:
                path = vue_match.group(1).strip()
                if path and path.startswith("/") and path not in seen_paths:
                    parts = [p for p in path.split("/") if p]
                    if len(parts) >= 1:
                        seen_paths.add(path)
                        module = parts[0].lower()
                        page_name = parts[-1] if len(parts) > 1 else module
                        extra_pages.append(PageDefinition(
                            path=path,
                            route_name=page_name.replace("-", " ").replace("_", " ").title(),
                            component="".join(p.title().replace("-", "") for p in parts),
                            module=module,
                            requirements=[],
                        ))
        
        # 去重：移除已在 _parse_pages_from_requirements 中解析的页面
        all_routes = self._parse_all_routes_from_doc()
        for route in all_routes:
            if route.path not in seen_paths:
                seen_paths.add(route.path)
                extra_pages.append(route)
        
        return extra_pages

    def _extract_pages_from_path(self, text: str, default_module: str) -> List[PageDefinition]:
        """从路径文本中提取页面定义。"""
        pages = []
        path_parts = re.findall(r"/([a-zA-Z][a-zA-Z0-9_-]*)", text)
        
        if len(path_parts) >= 2:
            module = path_parts[0]
            page_name = path_parts[-1]
            if page_name not in ("list", "index", "detail", "create", "edit"):
                path = "/" + "/".join(path_parts)
                component = "".join(p.title().replace("-", "") for p in path_parts)
                
                pages.append(PageDefinition(
                    path=path,
                    route_name=page_name.replace("-", " ").replace("_", " ").title(),
                    component=component,
                    module=module,
                    requirements=[],
                ))
        
        return pages

    def _parse_all_routes_from_doc(self) -> List[PageDefinition]:
        """从文档中解析所有路由路径。"""
        pages = []
        seen_paths = set()
        
        route_patterns = [
            r"['\"](/[a-zA-Z][a-zA-Z0-9_-]*(?:/[a-zA-Z][a-zA-Z0-9_-]*)*)['\"]",
            r"path:\s*['\"](/[a-zA-Z][a-zA-Z0-9_-]*(?:/[a-zA-Z][a-zA-Z0-9_-]*)*)['\"]",
            r"routes?\s*[=:]\s*\[([^\]]+)\]",
        ]
        
        for pattern in route_patterns:
            matches = re.finditer(pattern, self.doc_content, re.IGNORECASE)
            for match in matches:
                route_text = match.group(1) if match.lastindex else match.group(0)
                paths = re.findall(r"/[a-zA-Z][a-zA-Z0-9_-]*", route_text)
                
                if len(paths) >= 1:
                    path = "".join(paths)
                    if path not in seen_paths and len(path) > 1:
                        seen_paths.add(path)
                        
                        path_parts = [p.lstrip("/") for p in paths]
                        module = path_parts[0] if path_parts else "common"
                        page_name = path_parts[-1] if path_parts else "index"
                        
                        pages.append(PageDefinition(
                            path=path,
                            route_name=page_name.replace("-", " ").replace("_", " ").title(),
                            component="".join(p.title().replace("-", "") for p in path_parts) + "View",
                            module=module,
                            requirements=[],
                        ))
        
        return pages

    def _parse_routes_from_pages(self, pages: List[PageDefinition]) -> List[RouteDefinition]:
        routes = []
        
        for page in pages:
            routes.append(RouteDefinition(
                path=page.path,
                name=page.route_name,
                component=page.component,
                module=page.module,
                meta={},
            ))
        
        return routes

    def _parse_api_modules_from_requirements(self, requirements: List[Requirement]) -> List[ApiModule]:
        modules = {}
        
        for req in requirements:
            if req.api_module and req.api_module not in modules:
                modules[req.api_module] = ApiModule(
                    name=req.api_module,
                    module=req.module,
                    endpoints=[],
                    types_file=f"src/types/{req.api_module}.ts",
                )
        
        return list(modules.values())

    def _parse_stores_from_modules(self, modules: List[str]) -> List[StoreDefinition]:
        stores = []
        
        for module in modules:
            stores.append(StoreDefinition(
                name=module,
                module=module,
                file_path=f"src/stores/{module}.ts",
            ))
        
        return stores

    def _extract_module_name(self, text: str) -> str:
        text = text.strip()
        if not text or text == "-":
            return "common"
        
        match = re.search(r"M-([A-Z]+)", text)
        if match:
            return match.group(1).lower()
        
        return text.lower().replace(" ", "_")

    def _extract_page_path(self, text: str) -> Optional[str]:
        text = text.strip()
        if not text or text == "-":
            return None
        
        paths = [p.strip() for p in text.split(",")]
        return paths[0] if paths else None

    def _extract_route_name(self, text: str) -> Optional[str]:
        text = text.strip()
        if not text or text == "-":
            return None
        return text.split(",")[0].strip() if "," in text else text

    def _extract_api_module(self, text: str) -> Optional[str]:
        text = text.strip()
        if not text or text == "-":
            return None
        return text.split(",")[0].strip() if "," in text else text

    def _path_to_component(self, path: str) -> str:
        parts = [p for p in path.split("/") if p and p not in ["", "mobile"]]
        if not parts:
            return "Home"
        
        component_parts = []
        for part in parts:
            if part.startswith(":"):
                component_parts.append(part[1:].title())
            else:
                component_parts.append(part.title().replace("-", ""))
        
        return "".join(component_parts) + "View"

    def _path_to_route_name(self, path: str) -> str:
        return path.strip("/").replace("/", "-").replace(":", "")

    def _extract_modules_from_matrix(self) -> List[str]:
        modules = set()
        
        for req in self.parse_coverage_matrix().requirements:
            if req.module:
                modules.add(req.module)
        
        return sorted(list(modules))
