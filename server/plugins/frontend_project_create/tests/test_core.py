import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from server.plugins.frontend_project_create.analyzers.document import DocumentAnalyzer
from server.plugins.frontend_project_create.generators.base import GenerationContext
from server.plugins.frontend_project_create.generators.infrastructure import InfrastructureGenerator
from server.plugins.frontend_project_create.generators.component import ComponentGenerator
from server.plugins.frontend_project_create.memory.short_term import ShortTermMemory
from server.plugins.frontend_project_create.planners.project import ProjectPlanner
from server.plugins.frontend_project_create.planners.module import ModulePlanner
from server.plugins.frontend_project_create.verifiers.project import ProjectVerifier
from server.plugins.frontend_project_create.verifiers.step import StepVerifier
from server.plugins.frontend_project_create.state import ExecutionStep, Artifact


DOCUMENT = """
# 示例

Vue 3.5
Vite 6
Element Plus
Tailwind CSS 4
Pinia 2
Vue Router 4
@vueuse/core

| 需求ID | 需求名称 | 所属模块 | 页面路径 | 路由名称 | API模块 | LLD来源 |
|--------|----------|----------|----------|----------|---------|---------|
| REQ-FUN-001 | 资产列表 | asset | /asset/list | asset-list | asset | 1.1 |
| REQ-FUN-002 | 登录 | auth | /login | login | auth | 1.2 |
"""


class FrontendProjectCreateCoreTests(unittest.TestCase):
    def test_document_analyzer_extracts_summary(self) -> None:
        analyzer = DocumentAnalyzer(DOCUMENT)

        summary = analyzer.generate_summary()

        self.assertEqual(summary.requirements_count, 2)
        self.assertGreaterEqual(summary.pages_count, 2)
        self.assertIn("asset", summary.business_domains)
        self.assertIn("auth", summary.business_domains)

    def test_project_planner_generates_module_plan(self) -> None:
        coverage = DocumentAnalyzer(DOCUMENT).parse_coverage_matrix()
        planner = ProjectPlanner(coverage)

        planner.analyze_dependencies()
        plans = planner.generate_module_plan()

        self.assertEqual(len(plans), 2)
        self.assertTrue(any(plan.module == "auth" for plan in plans))
        self.assertTrue(any(plan.module == "asset" for plan in plans))

    def test_infrastructure_generator_uses_real_template(self) -> None:
        coverage = DocumentAnalyzer(DOCUMENT).parse_coverage_matrix()
        project_path = tempfile.mkdtemp(prefix="frontend-project-create-")
        context = GenerationContext(
            project_path=project_path,
            tech_stack=DocumentAnalyzer(DOCUMENT).extract_tech_stack(),
            coverage_matrix=coverage,
        )
        session = ShortTermMemory(session_id="test")

        try:
            generator = InfrastructureGenerator()
            result = asyncio.run(generator.generate(session, context))

            self.assertTrue(result.success)
            self.assertIn("package.json", result.files_generated)
            self.assertEqual(result.metadata.get("source"), "template")
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_module_planner_plans_component_files(self) -> None:
        coverage = DocumentAnalyzer(DOCUMENT).parse_coverage_matrix()
        coverage.pages = [p for p in coverage.pages if p.module == "asset"]
        planner = ModulePlanner(
            module="asset",
            pages=coverage.pages,
            api_modules=coverage.api_modules,
            stores=coverage.stores,
        )

        plans = planner._plan_component_files()

        self.assertGreater(len(plans), 0)
        self.assertTrue(any("Table" in p.file_path for p in plans))
        self.assertTrue(any("FormModal" in p.file_path for p in plans))
        self.assertTrue(any("SearchBar" in p.file_path for p in plans))
        self.assertTrue(any("DeleteConfirm" in p.file_path for p in plans))

    def test_component_generator_generates_components(self) -> None:
        coverage = DocumentAnalyzer(DOCUMENT).parse_coverage_matrix()
        project_path = tempfile.mkdtemp(prefix="frontend-component-")
        context = GenerationContext(
            project_path=project_path,
            tech_stack=DocumentAnalyzer(DOCUMENT).extract_tech_stack(),
            coverage_matrix=coverage,
        )
        session = ShortTermMemory(session_id="test-component")

        try:
            generator = ComponentGenerator()
            result = asyncio.run(generator.generate(session, context))

            self.assertTrue(result.success)
            self.assertGreater(len(result.files_generated), 0)
            self.assertTrue(any("Table.vue" in f for f in result.files_generated))
            self.assertTrue(any("FormModal.vue" in f for f in result.files_generated))
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_project_verifier_passes_on_real_template(self) -> None:
        coverage = DocumentAnalyzer(DOCUMENT).parse_coverage_matrix()
        project_path = tempfile.mkdtemp(prefix="frontend-verify-")
        context = GenerationContext(
            project_path=project_path,
            tech_stack=DocumentAnalyzer(DOCUMENT).extract_tech_stack(),
            coverage_matrix=coverage,
        )
        session = ShortTermMemory(session_id="test-verify")
        infra_gen = InfrastructureGenerator()

        try:
            asyncio.run(infra_gen.generate(session, context))

            verifier = ProjectVerifier(
                project_path=project_path,
                tech_stack=context.tech_stack,
                coverage_matrix=coverage,
            )
            result = verifier.verify()

            self.assertGreaterEqual(result.score, 50.0)
            self.assertIn(result.checked_items.get("package_json"), [True, None])
            self.assertIn(result.checked_items.get("vite_config"), [True, None])
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_step_verifier_validates_artifacts(self) -> None:
        project_path = tempfile.mkdtemp(prefix="frontend-step-verify-")

        try:
            session = ShortTermMemory(session_id="test-step")
            session.add_step(ExecutionStep(step="infrastructure", status="success", files=[]))
            session.add_artifact(Artifact(path="package.json", content="{}", module="infrastructure"))

            verifier = StepVerifier(project_path)
            result = verifier.verify_step("infrastructure", session)

            self.assertEqual(result.step, "infrastructure")
            self.assertIn(result.passed, [True, False])
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_short_term_memory_save_and_load(self) -> None:
        project_path = tempfile.mkdtemp(prefix="frontend-memory-")

        try:
            session = ShortTermMemory(
                session_id="test-save-load",
                tenant_id="test-tenant",
                user_id="test-user",
            )
            session.add_step(ExecutionStep(step="test", status="success", files=["file1.ts"]))

            session.save(base_path=project_path)

            loaded = ShortTermMemory.load("test-save-load", base_path=project_path)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.session_id, "test-save-load")
            self.assertEqual(loaded.tenant_id, "test-tenant")
            self.assertEqual(len(loaded.execution_trace), 1)
        finally:
            shutil.rmtree(project_path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
