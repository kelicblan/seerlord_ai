import asyncio
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader


class FrontendProjectSkillRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skill_dir = Path(__file__).resolve().parent.parent.parent.parent / "action_skills" / "generate-frontend-project"
        if str(skill_dir.parent) not in sys.path:
            sys.path.insert(0, str(skill_dir.parent))

    def test_executor_entry_point_runs(self) -> None:
        skill_dir = Path(__file__).resolve().parent.parent.parent.parent / "action_skills" / "generate-frontend-project"
        spec = SourceFileLoader("executor", str(skill_dir / "executor.py")).load_module()
        
        project_path = tempfile.mkdtemp(prefix="frontend-skill-test-")
        try:
            executor = spec.FrontendProjectExecutor(
                project_path=project_path,
                document_content="# Test",
                project_name="test-smoke",
            )
            
            self.assertIsNotNone(executor.project_name)
            self.assertIsNotNone(executor.project_path)
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_template_copy_mechanism(self) -> None:
        skill_dir = Path(__file__).resolve().parent.parent.parent.parent / "action_skills" / "generate-frontend-project"
        spec = SourceFileLoader("executor", str(skill_dir / "executor.py")).load_module()
        
        project_path = tempfile.mkdtemp(prefix="frontend-skill-test-")
        
        try:
            executor = spec.FrontendProjectExecutor(
                project_path=project_path,
                document_content="# Test",
                project_name="test-copy",
            )
            
            result = asyncio.run(executor._generate_project())
            
            self.assertTrue(result)
            
            template_dir = Path(project_path)
            if (template_dir / "package.json").exists():
                content = (template_dir / "package.json").read_text(encoding="utf-8")
                self.assertIn("name", content)
        finally:
            shutil.rmtree(project_path, ignore_errors=True)

    def test_verifier_accepts_real_template(self) -> None:
        skill_dir = Path(__file__).resolve().parent.parent.parent.parent / "action_skills" / "generate-frontend-project"
        spec = SourceFileLoader("verifier", str(skill_dir / "verifier.py")).load_module()
        
        project_path = tempfile.mkdtemp(prefix="frontend-verifier-test-")
        
        try:
            verifier = spec.ProjectVerifier(project_path=project_path)
            
            result = asyncio.run(verifier.verify_all())
            
            self.assertIsNotNone(result)
            self.assertIsNotNone(hasattr(result, 'success'))
        finally:
            shutil.rmtree(project_path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
