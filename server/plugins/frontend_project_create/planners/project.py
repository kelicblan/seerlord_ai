from typing import List, Dict, Set, Optional
from enum import Enum

from ..analyzers.structure import CoverageMatrix
from ..state import ModulePlan


class ProjectComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DependencyGraph:
    """维护模块依赖关系并提供拓扑排序能力。"""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, Set[str]] = {}
        self.in_degree: Dict[str, int] = {}
        self.out_degree: Dict[str, int] = {}

    def add_node(self, node: str) -> None:
        if node not in self.nodes:
            self.nodes.add(node)
            self.edges[node] = set()
            self.in_degree[node] = 0
            self.out_degree[node] = 0

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.add_node(from_node)
        self.add_node(to_node)
        
        if to_node not in self.edges[from_node]:
            self.edges[from_node].add(to_node)
            self.out_degree[from_node] += 1
            self.in_degree[to_node] += 1

    def topological_sort(self) -> List[str]:
        in_degree_copy = self.in_degree.copy()
        queue = [n for n in self.nodes if in_degree_copy[n] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.edges[node]:
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(self.nodes):
            return list(self.nodes)
        
        return result

    def get_dependencies(self, node: str) -> Set[str]:
        deps = set()
        for n, neighbors in self.edges.items():
            if node in neighbors:
                deps.add(n)
        return deps


class ProjectPlanner:
    """基于覆盖矩阵生成模块依赖与执行计划。"""

    def __init__(self, coverage_matrix: CoverageMatrix):
        self.coverage_matrix = coverage_matrix
        self.modules = coverage_matrix.get_all_modules()
        self.dependency_graph = DependencyGraph()

    def analyze_dependencies(self) -> DependencyGraph:
        self._build_dependency_graph()
        return self.dependency_graph

    def generate_module_plan(self) -> List[ModulePlan]:
        plans = []
        sorted_modules = self.dependency_graph.topological_sort()
        
        base_priority = 100
        
        for i, module in enumerate(sorted_modules):
            dependencies = list(self.dependency_graph.get_dependencies(module))
            
            pages = self.coverage_matrix.get_pages_by_module(module)
            apis = self.coverage_matrix.get_api_modules_by_module(module)
            stores = [s for s in self.coverage_matrix.stores if s.module == module]
            
            plan = ModulePlan(
                name=module,
                module=module,
                priority=base_priority - i * 10,
                dependencies=dependencies,
                status="pending",
                files_generated=[],
            )
            plans.append(plan)
        
        return plans

    def estimate_complexity(self) -> ProjectComplexity:
        total_requirements = len(self.coverage_matrix.requirements)
        total_pages = len(self.coverage_matrix.pages)
        total_routes = len(self.coverage_matrix.routes)
        total_api_modules = len(self.coverage_matrix.api_modules)
        total_stores = len(self.coverage_matrix.stores)
        num_modules = len(self.modules)
        
        score = (
            total_requirements * 1 +
            total_pages * 2 +
            total_routes * 1.5 +
            total_api_modules * 3 +
            total_stores * 2 +
            num_modules * 5
        )
        
        if score < 100:
            return ProjectComplexity.LOW
        elif score < 300:
            return ProjectComplexity.MEDIUM
        else:
            return ProjectComplexity.HIGH

    def _build_dependency_graph(self) -> None:
        for module in self.modules:
            self.dependency_graph.add_node(module)
        
        auth_module = self._find_auth_module()
        if auth_module:
            for module in self.modules:
                if module != auth_module:
                    self.dependency_graph.add_edge(auth_module, module)
        
        for api in self.coverage_matrix.api_modules:
            for page in self.coverage_matrix.pages:
                if page.module == api.module:
                    continue
                if any(r.api_module == api.name for r in self.coverage_matrix.requirements if r.page_path == page.path):
                    if page.module != api.module:
                        self.dependency_graph.add_edge(api.module, page.module)

    def _find_auth_module(self) -> Optional[str]:
        for module in self.modules:
            if "auth" in module.lower() or "login" in module.lower():
                return module
        if self.modules:
            return self.modules[0]
        return None

    def get_generation_order(self) -> List[str]:
        return self.dependency_graph.topological_sort()

    def get_module_info(self, module: str) -> Dict[str, object]:
        return {
            "module": module,
            "pages": self.coverage_matrix.get_pages_by_module(module),
            "routes": self.coverage_matrix.get_routes_by_module(module),
            "api_modules": self.coverage_matrix.get_api_modules_by_module(module),
            "requirements": self.coverage_matrix.get_requirements_by_module(module),
            "dependencies": list(self.dependency_graph.get_dependencies(module)),
        }
