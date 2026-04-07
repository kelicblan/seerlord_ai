import json
import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger

from ..memory.short_term import ShortTermMemory
from ..analyzers.structure import TechStack, CoverageMatrix


class GenerationResult(BaseModel):
    """描述单个生成阶段的执行结果。"""

    success: bool
    files_generated: List[str] = Field(default_factory=list)
    files_content: Dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerationContext(BaseModel):
    """封装生成阶段所需的上下文信息。"""

    project_path: str
    tech_stack: TechStack
    coverage_matrix: CoverageMatrix
    current_module: Optional[str] = None
    session_context: str = ""


class BaseGenerator(ABC):
    """所有生成器的抽象基类。"""

    def __init__(self):
        self._llm_client = None

    @abstractmethod
    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        pass

    def _save_files(self, files: Dict[str, str], project_path: Path) -> List[str]:
        """将生成的文件写入磁盘，使用传入的 project_path 而非 self.project_path。"""
        saved_files = []
        project_path = Path(project_path)
        for file_path, content in files.items():
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_files.append(file_path)
            except Exception as e:
                logger.exception("Failed to save generated file {}", file_path)

        return saved_files

    def _save_file(self, file_path: str, content: str, project_path: str) -> bool:
        """保存单个文件到磁盘。"""
        try:
            full_path = Path(project_path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Saved file: {}", full_path)
            return True
        except Exception as e:
            logger.error("Failed to save file {}: {}", file_path, e)
            return False

    def _parse_json_output(self, raw_output: str) -> Dict[str, Any]:
        """从原始 LLM 输出中提取 JSON 结构，支持 JSON 代码块和平铺 JSON。"""
        output = raw_output.strip()
        
        json_patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"```\s*(\{.*?\})\s*```",
        ]
        for pattern in json_patterns:
            matches = re.finditer(pattern, output, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        if output.startswith("{"):
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                pass
        
        return {}

    def _extract_all_json_blocks(self, raw_output: str) -> List[Dict[str, Any]]:
        """从原始 LLM 输出中提取所有 JSON 代码块。"""
        results = []
        json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        for block in json_blocks:
            try:
                results.append(json.loads(block))
            except json.JSONDecodeError:
                continue
        return results

    def _parse_files_from_json(self, json_data: Dict[str, Any]) -> Dict[str, str]:
        """从 JSON 结构中提取文件路径与内容映射。"""
        files = {}
        
        if "files" in json_data and isinstance(json_data["files"], dict):
            files.update(json_data["files"])
        
        for key, value in json_data.items():
            if key != "files" and isinstance(value, str) and (
                value.startswith("import ") or
                "export " in value or
                "<template>" in value or
                "export default" in value
            ):
                if key.endswith((".ts", ".vue", ".js", ".json")):
                    files[key] = value
        
        return files

    def _invoke_llm(
        self,
        prompt: str,
        context: GenerationContext,
        max_retries: int = 2
    ) -> str:
        """调用底层 LLM，并在失败时执行有限重试。"""
        if self._llm_client is None:
            self._llm_client = self._create_llm_client()
        
        for attempt in range(max_retries):
            try:
                response = self._llm_client.generate(prompt)
                if response and len(response) > 100:
                    return response
            except Exception:
                if attempt == max_retries - 1:
                    raise
                continue
        
        return ""

    def _create_llm_client(self):
        from server.kernel.llm import LLMClient
        return LLMClient()

    def _run_command(
        self,
        command: str,
        cwd: str,
        timeout: int = 300
    ) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                shlex.split(command),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except Exception as e:
            return -1, "", str(e)

    def _check_typescript_syntax(
        self,
        project_path: str,
        file_path: str
    ) -> tuple[bool, str]:
        full_path = Path(project_path) / file_path
        if not full_path.exists():
            return True, "File not found"
        
        _, stdout, stderr = self._run_command(
            f"npx tsc --noEmit --skipLibCheck {file_path}",
            cwd=project_path,
            timeout=60
        )
        
        if "error TS" in stderr:
            return False, stderr
        return True, ""

    def _get_file_content(
        self,
        project_path: str,
        file_path: str
    ) -> Optional[str]:
        full_path = Path(project_path) / file_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
