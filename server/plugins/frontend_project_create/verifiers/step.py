from typing import Dict, List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger

from ..memory.short_term import ShortTermMemory
from ..state import ExecutionStep


class StepVerificationResult(BaseModel):
    step: str
    passed: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    artifacts_checked: int = 0
    metadata: Dict[str, object] = Field(default_factory=dict)


class StepVerifier:
    """在生成流水线的每个阶段之后进行验证，确保该阶段产出有效。"""

    STEP_VALIDATORS: Dict[str, callable] = {}

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()

    def verify_step(
        self,
        step_name: str,
        session: ShortTermMemory,
    ) -> StepVerificationResult:
        validator = self.STEP_VALIDATORS.get(step_name)
        if validator:
            return validator(self, session)
        return self._default_verify_step(step_name, session)

    def verify_all_steps(self, session: ShortTermMemory) -> Dict[str, StepVerificationResult]:
        results = {}
        for step in session.execution_trace:
            results[step.step] = self.verify_step(step.step, session)
        return results

    def _default_verify_step(
        self,
        step_name: str,
        session: ShortTermMemory,
    ) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == step_name]
        errors = []
        warnings = []

        for artifact in artifacts:
            if not artifact.path:
                errors.append(f"Artifact missing path: {artifact}")
                continue
            full_path = self.project_path / artifact.path
            if not full_path.exists():
                errors.append(f"Generated file does not exist: {artifact.path}")

        if not artifacts:
            warnings.append(f"No artifacts generated for step: {step_name}")

        return StepVerificationResult(
            step=step_name,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )

    def verify_infrastructure_step(self, session: ShortTermMemory) -> StepVerificationResult:
        errors = []
        warnings = []

        required_files = [
            "package.json",
            "vite.config.ts",
            "tsconfig.json",
            "src/main.ts",
            "src/App.vue",
            "index.html",
        ]
        for file in required_files:
            if not (self.project_path / file).exists():
                errors.append(f"Missing required infrastructure file: {file}")

        pkg = self.project_path / "package.json"
        if pkg.exists():
            try:
                import json
                data = json.loads(pkg.read_text(encoding="utf-8"))
                if "scripts" not in data:
                    errors.append("package.json missing 'scripts' field")
                if "dev" not in data.get("scripts", {}):
                    warnings.append("package.json missing 'dev' script")
            except Exception as e:
                errors.append(f"package.json parse error: {e}")

        return StepVerificationResult(
            step="infrastructure",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(required_files),
        )

    def verify_types_step(self, session: ShortTermMemory) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == "types"]
        errors = []
        warnings = []

        for artifact in artifacts:
            if artifact.content and "export interface" not in artifact.content and "export type" not in artifact.content:
                errors.append(f"Type file missing exports: {artifact.path}")

        return StepVerificationResult(
            step="types",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )

    def verify_mock_data_step(self, session: ShortTermMemory) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == "mock_data"]
        errors = []
        warnings = []

        for artifact in artifacts:
            if artifact.content and "export" not in artifact.content:
                errors.append(f"Mock data file missing exports: {artifact.path}")

        return StepVerificationResult(
            step="mock_data",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )

    def verify_api_step(self, session: ShortTermMemory) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == "api"]
        errors = []
        warnings = []

        for artifact in artifacts:
            if artifact.content and "export" not in artifact.content:
                errors.append(f"API file missing exports: {artifact.path}")

        return StepVerificationResult(
            step="api",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )

    def verify_business_step(self, session: ShortTermMemory) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == "business"]
        errors = []
        warnings = []

        for artifact in artifacts:
            if artifact.content:
                if artifact.path.endswith(".ts") and "export" not in artifact.content:
                    errors.append(f"Business file missing exports: {artifact.path}")
                if artifact.path.endswith(".vue") and "<template>" not in artifact.content:
                    errors.append(f"Vue file missing template: {artifact.path}")

        return StepVerificationResult(
            step="business",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )

    def verify_views_step(self, session: ShortTermMemory) -> StepVerificationResult:
        artifacts = [a for a in session.generated_artifacts if a.module == "views"]
        errors = []
        warnings = []

        for artifact in artifacts:
            if artifact.content:
                if "<template>" not in artifact.content:
                    errors.append(f"View missing <template>: {artifact.path}")
                if "<script" not in artifact.content:
                    errors.append(f"View missing <script>: {artifact.path}")

        return StepVerificationResult(
            step="views",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            artifacts_checked=len(artifacts),
        )


StepVerifier.STEP_VALIDATORS = {
    "infrastructure": StepVerifier.verify_infrastructure_step,
    "types": StepVerifier.verify_types_step,
    "mock_data": StepVerifier.verify_mock_data_step,
    "api": StepVerifier.verify_api_step,
    "business": StepVerifier.verify_business_step,
    "views": StepVerifier.verify_views_step,
}
