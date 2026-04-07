import json
import re
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger

from ..state import TechStack, CoverageMatrix, ModulePlan


def _parse_json_with_comments(text: str) -> dict:
    """解析包含 JavaScript 注释的类 JSON 文件（如 tsconfig.json）。"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return json.loads(text)


def _read_file_text(path: Path) -> str:
    """读取文本文件，优先 UTF-8，失败则降级到 latin-1。"""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


class ProjectVerificationResult(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=100.0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checked_items: Dict[str, bool] = Field(default_factory=dict)
    missing_files: List[str] = Field(default_factory=list)
    broken_imports: List[str] = Field(default_factory=list)


class ProjectVerifier:
    """在生成完成后进行项目级完整性验证，包括文件结构、导入关系、配置一致性。"""

    def __init__(
        self,
        project_path: str,
        tech_stack: Optional[TechStack] = None,
        coverage_matrix: Optional[CoverageMatrix] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.tech_stack = tech_stack
        self.coverage_matrix = coverage_matrix

    def verify(self) -> ProjectVerificationResult:
        results = [
            self._check_file_structure(),
            self._check_package_json(),
            self._check_vite_config(),
            self._check_tsconfig(),
            self._check_router_config(),
            self._check_import_relationships(),
            self._check_coverage_completeness(),
        ]

        all_errors: List[str] = []
        all_warnings: List[str] = []
        all_missing: List[str] = []
        all_broken: List[str] = []
        passed_count = sum(1 for r in results if r.passed)

        for r in results:
            all_errors.extend(r.errors)
            all_warnings.extend(r.warnings)
            all_missing.extend(r.missing_files)
            all_broken.extend(r.broken_imports)

        score = (passed_count / len(results)) * 100 if results else 0.0

        return ProjectVerificationResult(
            passed=len(all_errors) == 0,
            score=round(score, 1),
            errors=all_errors,
            warnings=all_warnings,
            missing_files=all_missing,
            broken_imports=all_broken,
        )

    def _check_file_structure(self) -> ProjectVerificationResult:
        required_structure = [
            "package.json",
            "vite.config.ts",
            "tsconfig.json",
            "index.html",
            "src/main.ts",
            "src/App.vue",
            "src/router/index.ts",
            "src/stores",
            "src/api",
            "src/views",
        ]
        errors = []
        warnings = []
        missing = []

        for item in required_structure:
            path = self.project_path / item
            if item == "src/stores" or item == "src/api" or item == "src/views":
                if not path.exists():
                    missing.append(item)
            else:
                if not path.exists():
                    missing.append(item)

        if missing:
            errors.append(f"Missing {len(missing)} required files/directories")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if not missing else 50.0,
            errors=errors,
            warnings=warnings,
            missing_files=missing,
            checked_items={"file_structure": len(errors) == 0},
        )

    def _check_package_json(self) -> ProjectVerificationResult:
        pkg_path = self.project_path / "package.json"
        if not pkg_path.exists():
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=["package.json not found"],
                checked_items={"package_json": False},
            )

        try:
            content = _read_file_text(pkg_path)
        except Exception as e:
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=[f"package.json read error: {e}"],
                checked_items={"package_json": False},
            )

        errors = []
        warnings = []

        required_scripts = ["dev", "build"]
        for script in required_scripts:
            if f'"{script}"' not in content and f"'{script}'" not in content:
                errors.append(f"Missing required script: {script}")

        if self.tech_stack:
            if '"vue"' not in content and "'vue'" not in content:
                warnings.append("Vue not in dependencies")
            if '"vite"' not in content and "'vite'" not in content:
                warnings.append("Vite not in dependencies")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            checked_items={"package_json": True},
        )

    def _check_vite_config(self) -> ProjectVerificationResult:
        vite_path = self.project_path / "vite.config.ts"
        if not vite_path.exists():
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=["vite.config.ts not found"],
                checked_items={"vite_config": False},
            )

        content = vite_path.read_text(encoding="utf-8")
        errors = []
        warnings = []

        if "defineConfig" not in content:
            errors.append("vite.config.ts missing defineConfig")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            checked_items={"vite_config": True},
        )

    def _check_tsconfig(self) -> ProjectVerificationResult:
        tsconfig_path = self.project_path / "tsconfig.json"
        if not tsconfig_path.exists():
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=["tsconfig.json not found"],
                checked_items={"tsconfig": False},
            )

        try:
            content = _read_file_text(tsconfig_path)
        except Exception as e:
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=[f"tsconfig.json read error: {e}"],
                checked_items={"tsconfig": False},
            )

        errors = []
        warnings = []

        if "compilerOptions" not in content:
            tsconfig_app_path = self.project_path / "tsconfig.app.json"
            if tsconfig_app_path.exists():
                try:
                    app_content = _read_file_text(tsconfig_app_path)
                    if "compilerOptions" in app_content:
                        if "strict" not in app_content:
                            warnings.append("tsconfig.app.json: strict mode recommended")
                        if "jsx" not in app_content:
                            warnings.append("tsconfig.app.json: missing jsx option")
                    else:
                        errors.append("tsconfig.app.json missing compilerOptions")
                except Exception:
                    errors.append("tsconfig.json missing compilerOptions and tsconfig.app.json unreadable")
            else:
                errors.append("tsconfig.json missing compilerOptions")
        else:
            if "strict" not in content:
                warnings.append("tsconfig.json: strict mode recommended")
            if "jsx" not in content:
                warnings.append("tsconfig.json: missing jsx option")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            checked_items={"tsconfig": True},
        )

    def _check_router_config(self) -> ProjectVerificationResult:
        router_path = self.project_path / "src/router/index.ts"
        if not router_path.exists():
            return ProjectVerificationResult(
                passed=False,
                score=0.0,
                errors=["src/router/index.ts not found"],
                checked_items={"router": False},
            )

        content = router_path.read_text(encoding="utf-8")
        errors = []
        warnings = []

        if "createRouter" not in content and "createWebHistory" not in content:
            errors.append("Router config missing Vue Router setup")

        if self.coverage_matrix and self.coverage_matrix.routes:
            route_names = [r.name for r in self.coverage_matrix.routes]
            for name in route_names:
                if name not in content:
                    warnings.append(f"Route '{name}' defined in coverage but not found in router config")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            checked_items={"router": True},
        )

    def _check_import_relationships(self) -> ProjectVerificationResult:
        errors = []
        warnings = []
        broken_imports: List[str] = []

        ts_files = list(self.project_path.rglob("*.ts"))
        vue_files = list(self.project_path.rglob("*.vue"))
        all_source_files = ts_files + vue_files

        all_paths: Set[str] = set()
        for f in all_source_files:
            rel = f.relative_to(self.project_path)
            all_paths.add(str(rel))
            all_paths.add("./" + str(rel))
            all_paths.add("../" + str(rel))

        import_pattern = re.compile(r"""import\s+.*?from\s+['"]([^'"]+)['"]""")

        for f in all_source_files:
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue

            for match in import_pattern.finditer(content):
                import_path = match.group(1)

                if import_path.startswith("@/") or import_path.startswith("~/"):
                    resolved = import_path.replace("@/", "src/").replace("~/", "src/")
                    resolved_path = self.project_path / resolved
                    if not resolved_path.exists():
                        if not resolved_path.with_suffix(".ts").exists() and not resolved_path.with_suffix(".vue").exists():
                            broken_imports.append(f"{f.relative_to(self.project_path)} -> {import_path}")

                elif import_path.startswith(".") and not import_path.endswith(".css"):
                    resolved = (f.parent / import_path).resolve()
                    if not resolved.exists():
                        if not resolved.with_suffix(".ts").exists() and not resolved.with_suffix(".vue").exists():
                            broken_imports.append(f"{f.relative_to(self.project_path)} -> {import_path}")

        if broken_imports:
            errors.append(f"Found {len(broken_imports)} broken imports")
            logger.warning(f"Broken imports detected: {broken_imports[:5]}")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            broken_imports=broken_imports,
            checked_items={"imports": len(broken_imports) == 0},
        )

    def _check_coverage_completeness(self) -> ProjectVerificationResult:
        if not self.coverage_matrix:
            return ProjectVerificationResult(
                passed=True,
                score=100.0,
                warnings=["No coverage matrix to verify"],
                checked_items={"coverage": True},
            )

        errors = []
        warnings = []
        views_dir = self.project_path / "src/views"

        for page in self.coverage_matrix.pages:
            path_parts = page.path.strip("/").split("/")
            view_name = "".join(p.title().replace("-", "") for p in path_parts if p and not p.startswith(":"))
            view_file = views_dir / page.path.strip("/") / f"{view_name}.vue"

            if not view_file.exists():
                warnings.append(f"Page defined in coverage but file not generated: {view_file}")

        for api in self.coverage_matrix.api_modules:
            api_file = self.project_path / "src/api" / f"{api.name}.ts"
            if not api_file.exists():
                warnings.append(f"API defined in coverage but file not generated: {api_file}")

        return ProjectVerificationResult(
            passed=len(errors) == 0,
            score=100.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings,
            checked_items={"coverage": True},
        )
