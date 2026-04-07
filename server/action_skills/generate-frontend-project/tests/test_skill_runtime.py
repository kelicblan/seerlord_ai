import asyncio
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def load_module(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SKILL_DIR / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


parser_module = load_module("generate_frontend_project_parser_test", "parser.py")
verifier_module = load_module("generate_frontend_project_verifier_test", "verifier.py")
executor_module = load_module("generate_frontend_project_executor_test", "executor.py")


class GenerateFrontendProjectSkillTests(unittest.TestCase):
    def test_parser_supports_json_files_payload(self) -> None:
        raw_output = json.dumps(
            {
                "files": {
                    "src/api/demo.ts": "export const demo = 1",
                    "src/views/Demo.vue": "<template><div>demo</div></template>",
                }
            },
            ensure_ascii=False,
        )

        files, errors = parser_module.parse_generated_files(raw_output)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(files), 2)
        self.assertTrue(any(file.path == "src/api/demo.ts" for file in files))

    def test_verifier_basic_check_accepts_template(self) -> None:
        project_dir = Path(tempfile.mkdtemp(prefix="generate-frontend-project-"))
        try:
            shutil.copytree(SKILL_DIR / "template", project_dir, dirs_exist_ok=True)
            result = asyncio.run(verifier_module.ProjectVerifier(str(project_dir))._verify_basic())
            self.assertTrue(result.success, result.errors)
        finally:
            shutil.rmtree(project_dir, ignore_errors=True)

    def test_executor_copies_template(self) -> None:
        project_dir = Path(tempfile.mkdtemp(prefix="generate-frontend-project-executor-"))
        try:
            success, result = asyncio.run(
                executor_module.execute_frontend_project_generation(
                    document_content="demo",
                    project_path=str(project_dir),
                    project_name="demo",
                )
            )
            self.assertTrue(success)
            self.assertTrue((project_dir / "package.json").exists())
            self.assertGreater(result["files_generated"], 0)
        finally:
            shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
