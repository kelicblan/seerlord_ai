import time
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..state import (
    ProjectMetadata,
    DocumentSummary,
    ModulePlan,
    ExecutionStep,
    ErrorRecord,
    Artifact,
    TechStack,
    CoverageMatrix,
)


class ShortTermMemory:
    def __init__(
        self,
        session_id: str,
        tenant_id: str = "default",
        user_id: str = "default",
    ):
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.created_at = time.time()
        self.updated_at = time.time()
        
        self.project_metadata: Optional[ProjectMetadata] = None
        self.tech_stack: Optional[TechStack] = None
        self.coverage_matrix: Optional[CoverageMatrix] = None
        self.document_summary: Optional[DocumentSummary] = None
        
        self.module_plan: List[ModulePlan] = []
        self.execution_trace: List[ExecutionStep] = []
        self.error_trace: List[ErrorRecord] = []
        self.generated_artifacts: List[Artifact] = []
        
        self.knowledge_used: List[Dict[str, Any]] = []
        
        self.current_module_index: int = 0
        self.total_modules: int = 0
        self.current_iteration: int = 0
        self.max_iterations: int = 100

    def add_step(self, step: ExecutionStep) -> None:
        step.timestamp = time.time()
        self.execution_trace.append(step)
        self.updated_at = time.time()

    def add_error(self, error: ErrorRecord) -> None:
        self.error_trace.append(error)
        self.updated_at = time.time()

    def add_artifact(self, artifact: Artifact) -> None:
        self.generated_artifacts.append(artifact)
        self.updated_at = time.time()

    def update_module_status(
        self,
        module_name: str,
        status: str,
        files_generated: Optional[List[str]] = None
    ) -> None:
        for plan in self.module_plan:
            if plan.name == module_name:
                plan.status = status
                if files_generated:
                    plan.files_generated.extend(files_generated)
                break
        self.updated_at = time.time()

    def get_context_for_llm(self) -> str:
        context_parts = []
        
        context_parts.append(f"## 会话上下文 (Session: {self.session_id})")
        context_parts.append(f"当前迭代: {self.current_iteration}/{self.max_iterations}")
        context_parts.append(f"当前模块: {self.current_module_index}/{self.total_modules}")
        
        if self.project_metadata:
            context_parts.append(f"\n## 项目信息")
            context_parts.append(f"名称: {self.project_metadata.name}")
            context_parts.append(f"技术栈: {self.project_metadata.tech_stack}")
        
        if self.tech_stack:
            context_parts.append(f"\n## 技术栈")
            context_parts.append(f"- 框架: {self.tech_stack.framework}")
            context_parts.append(f"- 构建: {self.tech_stack.build}")
            context_parts.append(f"- UI: {self.tech_stack.ui}")
            context_parts.append(f"- 样式: {self.tech_stack.css}")
            context_parts.append(f"- 状态: {self.tech_stack.state}")
            context_parts.append(f"- 路由: {self.tech_stack.router}")
            context_parts.append(f"- 工具: {self.tech_stack.utils}")
        
        if self.document_summary:
            context_parts.append(f"\n## 文档摘要")
            context_parts.append(f"- 需求数量: {self.document_summary.requirements_count}")
            context_parts.append(f"- 页面数量: {self.document_summary.pages_count}")
            context_parts.append(f"- 路由数量: {self.document_summary.routes_count}")
            context_parts.append(f"- API模块: {self.document_summary.api_modules_count}")
            context_parts.append(f"- Store: {self.document_summary.stores_count}")
            context_parts.append(f"- 业务领域: {', '.join(self.document_summary.business_domains)}")
        
        if self.module_plan:
            context_parts.append(f"\n## 模块计划")
            for i, plan in enumerate(self.module_plan):
                context_parts.append(f"{i+1}. {plan.name} [{plan.status}]")
        
        if self.execution_trace:
            context_parts.append(f"\n## 执行轨迹")
            for step in self.execution_trace[-5:]:
                status_icon = "✓" if step.status == "success" else "✗"
                context_parts.append(f"{status_icon} {step.step}: {step.status}")
        
        if self.error_trace:
            context_parts.append(f"\n## 最近错误")
            for error in self.error_trace[-3:]:
                context_parts.append(f"- {error.step}: {error.error_type}")
                if error.root_cause:
                    context_parts.append(f"  根因: {error.root_cause}")
        
        if self.knowledge_used:
            context_parts.append(f"\n## 使用的知识")
            for knowledge in self.knowledge_used[-3:]:
                context_parts.append(f"- {knowledge.get('type', 'unknown')}: {knowledge.get('name', '')}")
        
        return "\n".join(context_parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "project_metadata": self.project_metadata.model_dump() if self.project_metadata else None,
            "tech_stack": self.tech_stack.model_dump() if self.tech_stack else None,
            "coverage_matrix": self.coverage_matrix.model_dump() if self.coverage_matrix else None,
            "document_summary": self.document_summary.model_dump() if self.document_summary else None,
            "module_plan": [
                p.model_dump() if hasattr(p, 'model_dump') else p
                for p in self.module_plan
            ],
            "execution_trace": [
                e.model_dump() if hasattr(e, 'model_dump') else e
                for e in self.execution_trace
            ],
            "error_trace": [
                e.model_dump() if hasattr(e, 'model_dump') else e
                for e in self.error_trace
            ],
            "generated_artifacts": [
                a.model_dump() if hasattr(a, 'model_dump') else a
                for a in self.generated_artifacts
            ],
            "knowledge_used": self.knowledge_used,
            "current_module_index": self.current_module_index,
            "total_modules": self.total_modules,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortTermMemory":
        memory = cls(
            session_id=data["session_id"],
            tenant_id=data.get("tenant_id", "default"),
            user_id=data.get("user_id", "default"),
        )
        memory.created_at = data.get("created_at", time.time())
        memory.updated_at = data.get("updated_at", time.time())
        
        if data.get("project_metadata"):
            memory.project_metadata = ProjectMetadata(**data["project_metadata"])
        if data.get("tech_stack"):
            memory.tech_stack = TechStack(**data["tech_stack"])
        if data.get("coverage_matrix"):
            memory.coverage_matrix = CoverageMatrix(**data["coverage_matrix"])
        if data.get("document_summary"):
            memory.document_summary = DocumentSummary(**data["document_summary"])
        
        memory.module_plan = [ModulePlan(**p) for p in data.get("module_plan", [])]
        memory.execution_trace = [ExecutionStep(**e) for e in data.get("execution_trace", [])]
        memory.error_trace = [ErrorRecord(**e) for e in data.get("error_trace", [])]
        memory.generated_artifacts = [Artifact(**a) for a in data.get("generated_artifacts", [])]
        memory.knowledge_used = data.get("knowledge_used", [])
        memory.current_module_index = data.get("current_module_index", 0)
        memory.total_modules = data.get("total_modules", 0)
        memory.current_iteration = data.get("current_iteration", 0)
        memory.max_iterations = data.get("max_iterations", 100)
        
        return memory

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ShortTermMemory":
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, base_path: str = "server/data/frontend_project_knowledge/sessions") -> None:
        from pathlib import Path
        session_dir = Path(base_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = session_dir / f"{self.session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        
        self.updated_at = time.time()

    @classmethod
    def load(cls, session_id: str, base_path: str = "server/data/frontend_project_knowledge/sessions") -> Optional["ShortTermMemory"]:
        from pathlib import Path
        session_file = Path(base_path) / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return cls.from_json(f.read())
        except Exception:
            return None
