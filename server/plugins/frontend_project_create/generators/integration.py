import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base import GenerationResult, GenerationContext
from .infrastructure import InfrastructureGenerator
from .types import TypeGenerator
from .mock_data import MockDataGenerator
from .api import ApiGenerator
from .business import BusinessLogicGenerator
from .views import ViewGenerator
from .component import ComponentGenerator
from .router_gen import RouterGenerator

from ..verifiers.step import StepVerifier, StepVerificationResult
from ..verifiers.project import ProjectVerifier, ProjectVerificationResult

from ..memory.short_term import ShortTermMemory
from ..memory.long_term import LongTermMemory
from ..state import ExecutionStep, ErrorRecord, Artifact


class GenerationPipeline:
    def __init__(
        self,
        project_path: str,
        long_term_memory: Optional[LongTermMemory] = None
    ):
        self.project_path = project_path
        self.long_term_memory = long_term_memory or LongTermMemory()
        
        self.infrastructure_generator = InfrastructureGenerator()
        self.type_generator = TypeGenerator()
        self.mock_data_generator = MockDataGenerator()
        self.api_generator = ApiGenerator()
        self.business_generator = BusinessLogicGenerator()
        self.view_generator = ViewGenerator()
        self.router_generator = RouterGenerator()
        self.component_generator = ComponentGenerator()
        
        self._step_verifier = StepVerifier(project_path)
        self._step_verification_results: List[StepVerificationResult] = []
        self._project_verification_result: Optional[ProjectVerificationResult] = None

    async def run(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        Path(self.project_path).mkdir(parents=True, exist_ok=True)
        
        session.current_iteration += 1
        
        try:
            result = await self._run_generation(session, context)
            
            if result.success:
                self._record_success(session, result)
            else:
                self._record_failure(session, result)
            
            return result
            
        except Exception as e:
            error = ErrorRecord(
                step="pipeline",
                error_type="pipeline_error",
                root_cause=str(e),
                attempts=[],
            )
            session.add_error(error)
            
            return GenerationResult(success=False, error=str(e))

    async def _run_generation(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        all_files = []
        
        step = ExecutionStep(step="infrastructure", status="running")
        session.add_step(step)
        infra_result = await self.infrastructure_generator.generate(session, context)
        if infra_result.success:
            step.status = "success"
            step.files = infra_result.files_generated
            all_files.extend(infra_result.files_generated)
            for file_path, content in infra_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="infrastructure"))
        else:
            step.status = "failed"
            step.error = infra_result.error
            return GenerationResult(success=False, error=infra_result.error)
        session.add_step(step)
        
        step = ExecutionStep(step="types", status="running")
        session.add_step(step)
        type_result = await self.type_generator.generate(session, context)
        if type_result.success:
            step.status = "success"
            step.files = type_result.files_generated
            all_files.extend(type_result.files_generated)
            for file_path, content in type_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="types"))
        session.add_step(step)
        
        step = ExecutionStep(step="mock_data", status="running")
        session.add_step(step)
        mock_result = await self.mock_data_generator.generate(session, context)
        if mock_result.success:
            step.status = "success"
            step.files = mock_result.files_generated
            all_files.extend(mock_result.files_generated)
            for file_path, content in mock_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="mock_data"))
        session.add_step(step)
        
        step = ExecutionStep(step="api", status="running")
        session.add_step(step)
        api_result = await self.api_generator.generate(session, context)
        if api_result.success:
            step.status = "success"
            step.files = api_result.files_generated
            all_files.extend(api_result.files_generated)
            for file_path, content in api_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="api"))
        session.add_step(step)
        
        step = ExecutionStep(step="business", status="running")
        session.add_step(step)
        business_result = await self.business_generator.generate(session, context)
        if business_result.success:
            step.status = "success"
            step.files = business_result.files_generated
            all_files.extend(business_result.files_generated)
            for file_path, content in business_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="business"))
        session.add_step(step)
        
        step = ExecutionStep(step="views", status="running")
        session.add_step(step)
        view_result = await self.view_generator.generate(session, context)
        if view_result.success:
            step.status = "success"
            step.files = view_result.files_generated
            all_files.extend(view_result.files_generated)
            for file_path, content in view_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="views"))
        session.add_step(step)
        
        step = ExecutionStep(step="router", status="running")
        session.add_step(step)
        router_result = await self.router_generator.generate(session, context)
        if router_result.success:
            step.status = "success"
            step.files = router_result.files_generated
            all_files.extend(router_result.files_generated)
            for file_path, content in router_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="router"))
        session.add_step(step)
        
        step = ExecutionStep(step="components", status="running")
        session.add_step(step)
        component_result = await self.component_generator.generate(session, context)
        if component_result.success:
            step.status = "success"
            step.files = component_result.files_generated
            all_files.extend(component_result.files_generated)
            for file_path, content in component_result.files_content.items():
                session.add_artifact(Artifact(path=file_path, content=content, module="components"))
        session.add_step(step)
        
        self._verify_steps(session)
        
        self._project_verification_result = self._verify_project(session, context)
        
        return GenerationResult(
            success=True,
            files_generated=all_files,
            metadata={
                "project_path": self.project_path,
                "total_files": len(all_files),
                "step_verifications": [r.model_dump() for r in self._step_verification_results],
                "project_verification": self._project_verification_result.model_dump() if self._project_verification_result else None,
            }
        )

    def _record_success(self, session: ShortTermMemory, result: GenerationResult) -> None:
        from ..memory.long_term import SuccessfulCase
        
        case = SuccessfulCase(
            id=f"case_{int(time.time())}",
            project_name=session.project_metadata.name if session.project_metadata else "unknown",
            document_type="frontend_project",
            modules=[p.name for p in session.module_plan] if session.module_plan else [],
            key_insights=["生成成功"],
            success_rate=1.0,
        )
        self.long_term_memory.add_successful_case(case)

    def _record_failure(self, session: ShortTermMemory, result: GenerationResult) -> None:
        from ..memory.long_term import FailedCase
        
        last_error = session.error_trace[-1] if session.error_trace else None
        
        case = FailedCase(
            id=f"case_{int(time.time())}",
            project_name=session.project_metadata.name if session.project_metadata else "unknown",
            document_type="frontend_project",
            error_type=last_error.error_type if last_error else "unknown",
            root_cause=last_error.root_cause if last_error else result.error,
            attempts=[a.model_dump() for a in session.error_trace],
            lessons_learned=["分析失败原因并改进"],
        )
        self.long_term_memory.add_failed_case(case)

    def _verify_steps(self, session: ShortTermMemory) -> List[StepVerificationResult]:
        self._step_verification_results = []
        for step in session.execution_trace:
            result = self._step_verifier.verify_step(step.step, session)
            self._step_verification_results.append(result)
        return self._step_verification_results

    def _verify_project(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> ProjectVerificationResult:
        verifier = ProjectVerifier(
            project_path=self.project_path,
            tech_stack=context.tech_stack,
            coverage_matrix=context.coverage_matrix,
        )
        return verifier.verify()

    def get_step_verification_results(self) -> List[StepVerificationResult]:
        return self._step_verification_results

    def get_project_verification_result(self) -> Optional[ProjectVerificationResult]:
        return self._project_verification_result
