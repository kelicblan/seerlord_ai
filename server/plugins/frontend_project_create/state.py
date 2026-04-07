from typing import TypedDict, Annotated, List, Optional, Tuple, Union, Dict, Any
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
import operator

from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    name: str
    tech_stack: Dict[str, str]
    description: Optional[str] = None


class DocumentSummary(BaseModel):
    requirements_count: int = 0
    pages_count: int = 0
    routes_count: int = 0
    api_modules_count: int = 0
    stores_count: int = 0
    business_domains: List[str] = Field(default_factory=list)


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


class CoverageMatrix(BaseModel):
    requirements: List[Requirement] = Field(default_factory=list)
    pages: List[PageDefinition] = Field(default_factory=list)
    routes: List[RouteDefinition] = Field(default_factory=list)
    api_modules: List[ApiModule] = Field(default_factory=list)
    stores: List[StoreDefinition] = Field(default_factory=list)


class ModulePlan(BaseModel):
    name: str
    module: str
    priority: int = 0
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"
    files_generated: List[str] = Field(default_factory=list)


class ExecutionStep(BaseModel):
    step: str
    status: str
    files: List[str] = Field(default_factory=list)
    timestamp: float = 0
    error: Optional[str] = None


class ErrorRecord(BaseModel):
    step: str
    error_type: str
    root_cause: Optional[str] = None
    attempts: List[Dict[str, Any]] = Field(default_factory=list)


class Artifact(BaseModel):
    path: str
    content: str
    module: Optional[str] = None
    type: str = "file"


class GenerationContext(BaseModel):
    project_path: str
    tech_stack: TechStack
    coverage_matrix: CoverageMatrix
    current_module: Optional[str] = None
    knowledge_used: List[str] = Field(default_factory=list)


class FrontendProjectCreateState(TypedDict):
    intent_title: str
    messages: Annotated[List[BaseMessage], add_messages]
    input_content: Optional[str]
    document_content: Optional[str]
    document_summary: Optional[DocumentSummary]
    tech_stack: Optional[TechStack]
    coverage_matrix: Optional[CoverageMatrix]
    module_plans: Optional[List[ModulePlan]]
    project_metadata: Optional[ProjectMetadata]
    project_path: Optional[str]
    generated_artifacts: Optional[List[Artifact]]
    execution_trace: Optional[List[ExecutionStep]]
    error_trace: Optional[List[ErrorRecord]]
    current_module_index: int
    total_modules: int
    generation_context: Optional[GenerationContext]
    tenant_id: str
    user_id: str
    memory_context: str
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
    total_tokens: int
    current_iteration: int
    max_iterations: int
    last_error: Optional[str]
    execution_id: Optional[str]
    result: Optional[dict]
    output_artifacts: Optional[List[dict]]
    status: Optional[str]
    error_message: Optional[str]
    verification_score: Optional[float]
    verification_errors: Optional[List[str]]
    verification_warnings: Optional[List[str]]
    vercel_url: Optional[str]
    download_url: Optional[str]
    install_ok: Optional[bool]
    build_ok: Optional[bool]
    build_msg: Optional[str]
    all_errors: Optional[List[str]]
    all_warnings: Optional[List[str]]
    lint_ok: Optional[bool]
    lint_msg: Optional[str]
    dev_ok: Optional[bool]
    dev_msg: Optional[str]


def create_initial_state(
    tenant_id: str = "default",
    user_id: str = "default",
    intent_title: str = "",
    document_content: str = ""
) -> FrontendProjectCreateState:
    return FrontendProjectCreateState(
        intent_title=intent_title,
        messages=[],
        input_content=document_content,
        document_content=document_content,
        document_summary=None,
        tech_stack=None,
        coverage_matrix=None,
        module_plans=None,
        project_metadata=None,
        project_path=None,
        generated_artifacts=[],
        execution_trace=[],
        error_trace=[],
        current_module_index=0,
        total_modules=0,
        generation_context=None,
        tenant_id=tenant_id,
        user_id=user_id,
        memory_context="",
        skills_context=None,
        used_skill_ids=[],
        total_tokens=0,
        current_iteration=0,
        max_iterations=100,
        last_error=None,
        execution_id=None,
        result=None,
        output_artifacts=[],
        status="pending",
        error_message=None,
    )
