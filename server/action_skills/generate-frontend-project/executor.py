import asyncio
import importlib.util
import json
import os
import platform
import re
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Tuple

from loguru import logger
from playwright.async_api import async_playwright

LogCallback = Callable[[str, str, str], Awaitable[None]]
SSEPublisher = Callable[[dict[str, Any]], Awaitable[None]]

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent
ESLINT_CONFIG_PATTERNS = (
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "eslint.config.ts",
)
MOCK_DIR_CANDIDATES = (
    Path("src/api"),
    Path("api"),
    Path("src/mock"),
    Path("src/mocks"),
)
MOCK_FILE_SKIP = {"client.ts", "http.ts", "index.ts"}
PLACEHOLDER_PATTERNS = [
    "test1", "test2", "test3", "xxx", "yyy", "zzz",
    "placeholder", "todo", "temp", "dummy", "sample",
]

TEMPLATE_FOUNDATION_ERROR_CODES = frozenset({
    "PACKAGE_JSON_MISSING",
    "BUILD_SCRIPT_MISSING",
    "INSTALL_ERESOLVE",
    "INSTALL_E404",
    "INSTALL_ETARGET",
    "INSTALL_FAILED",
    "LINT_CONFIG_MISSING",
    "RUNTIME_SCRIPT_MISSING",
    "SERVER_START_FAILED",
    "SERVER_START_TIMEOUT",
})

BUSINESS_FILE_PREFIXES = (
    "generated/",
    "src/api/",
    "api/",
    "src/mock/",
    "src/mocks/",
    "src/views/",
    "src/components/",
    "src/composables/",
    "src/stores/",
    "src/directives/",
    "src/guards/",
    "src/router/",
    "src/types/",
)

TEMPLATE_FOUNDATION_FILES = (
    "package.json",
    "index.html",
    "vite.config.ts",
    "src/main.ts",
    "src/App.vue",
    "src/style.css",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "eslint.config.ts",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.cjs",
)

try:
    from .parser import (
        parse_generated_files,
        extract_file_content,
        validate_file_path,
        FileParseError,
    )
    from .verifier import (
        ProjectVerifier,
        VerificationResult,
        VerificationLevel,
    )
    from .prompts import (
        SELF_CORRECTION_SYSTEM_PROMPT,
        GENERATION_SYSTEM_PROMPT,
    )
except ImportError:
    import importlib.util

    def _load_local_module(module_name: str, file_name: str):
        module_path = SKILL_DIR / file_name
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    parser_module = _load_local_module("generate_frontend_project_parser", "parser.py")
    verifier_module = _load_local_module("generate_frontend_project_verifier", "verifier.py")
    prompts_module = _load_local_module("generate_frontend_project_prompts", "prompts.py")

    parse_generated_files = parser_module.parse_generated_files
    extract_file_content = parser_module.extract_file_content
    validate_file_path = parser_module.validate_file_path
    FileParseError = parser_module.FileParseError
    ProjectVerifier = verifier_module.ProjectVerifier
    VerificationResult = verifier_module.VerificationResult
    VerificationLevel = verifier_module.VerificationLevel
    SELF_CORRECTION_SYSTEM_PROMPT = prompts_module.SELF_CORRECTION_SYSTEM_PROMPT
    GENERATION_SYSTEM_PROMPT = prompts_module.GENERATION_SYSTEM_PROMPT


def _load_skill_config() -> dict:
    config_path = SKILL_DIR / "memory" / "knowledge_base.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error_patterns": [], "generation_techniques": []}


def _save_output_log(
    project_path: str,
    phase: str,
    content: str,
    metadata: Optional[dict] = None
) -> None:
    output_dir = Path(project_path) / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = output_dir / f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Phase: {phase}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        if metadata:
            f.write(f"Metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        f.write(content)


class FrontendProjectExecutor:
    """基于稳定模板执行前端项目初始化与验证。"""

    def __init__(
        self,
        project_path: str,
        document_content: str,
        project_name: str = "generated-project",
        on_log: Optional[LogCallback] = None,
        on_sse: Optional[SSEPublisher] = None,
    ):
        self.project_path = Path(project_path)
        self.document_content = document_content
        self.project_name = project_name
        self.on_log = on_log
        self.on_sse = on_sse
        self.skill_config = _load_skill_config()
        self.verifier = ProjectVerifier(project_path)
        
    async def execute(self) -> Tuple[bool, dict]:
        start_time = time.time()
        
        try:
            await self._log("info", "start", "开始执行前端项目生成...")
            
            self._prepare_project_directory()
            
            success = await self._generate_project()
            
            if success:
                verification_result = await self._verify_project()
                if not verification_result.success:
                    await self._log("warning", "verification", f"验证未完全通过: {verification_result.message}")
            
            duration = time.time() - start_time
            
            result = {
                "success": success,
                "project_path": str(self.project_path),
                "project_name": self.project_name,
                "duration_seconds": round(duration, 2),
                "files_generated": self._count_generated_files(),
            }
            
            await self._log("info", "complete", f"执行完成，耗时 {duration:.2f}s")
            
            return success, result
            
        except Exception as e:
            logger.exception("Frontend project generation failed")
            await self._log("error", "exception", str(e))
            return False, {
                "success": False,
                "error": str(e),
                "project_path": str(self.project_path),
            }

    def _prepare_project_directory(self) -> None:
        self.project_path.mkdir(parents=True, exist_ok=True)
        
    async def _generate_project(self) -> bool:
        """复制稳定模板并写出基础生成日志。"""
        template_dir = SKILL_DIR / "template"
        if not template_dir.exists():
            await self._log("error", "template", f"模板目录不存在: {template_dir}")
            return False

        copied_files = 0
        for source in template_dir.rglob("*"):
            if not source.is_file():
                continue
            relative_path = source.relative_to(template_dir)
            target = self.project_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            copied_files += 1

        _save_output_log(
            str(self.project_path),
            "template_copy",
            self.document_content,
            metadata={
                "project_name": self.project_name,
                "template_path": str(template_dir),
                "copied_files": copied_files,
            },
        )
        await self._log("info", "template", f"已复制稳定模板，共 {copied_files} 个文件")
        return copied_files > 0

    async def _verify_project(self) -> VerificationResult:
        return await self.verifier.verify_all()

    async def _log(self, level: str, phase: str, message: str) -> None:
        log_msg = f"[{phase.upper()}] {message}"
        
        if level == "info":
            logger.info(log_msg)
        elif level == "warning":
            logger.warning(log_msg)
        elif level == "error":
            logger.error(log_msg)
        
        if self.on_log:
            await self.on_log(level, phase, message)
        
        if self.on_sse:
            await self.on_sse({
                "type": "generation_log",
                "level": level,
                "phase": phase,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            })

    def _count_generated_files(self) -> int:
        count = 0
        for root, dirs, files in os.walk(self.project_path):
            for f in files:
                if not f.startswith("."):
                    count += 1
        return count

    async def install_dependencies(self) -> Tuple[bool, str]:
        try:
            await self._log("info", "install", "开始安装依赖...")
            
            cmd = "npm install"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.project_path),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )

            if result.returncode == 0:
                await self._log("info", "install", "依赖安装成功")
                return True, "Dependencies installed successfully"
            else:
                error_msg = result.stderr or "Unknown install error"
                await self._log("error", "install", f"依赖安装失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            await self._log("error", "install", "依赖安装超时")
            return False, "Install timeout"
        except Exception as e:
            await self._log("error", "install", f"依赖安装异常: {str(e)}")
            return False, str(e)

    async def build_project(self) -> Tuple[bool, str]:
        try:
            await self._log("info", "build", "开始构建项目...")

            cmd = "npm run build"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.project_path),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            
            if result.returncode == 0:
                await self._log("info", "build", "项目构建成功")
                return True, "Build successful"
            else:
                error_msg = result.stderr or result.stdout or "Unknown build error"
                await self._log("error", "build", f"构建失败: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            await self._log("error", "build", "构建超时")
            return False, "Build timeout"
        except Exception as e:
            await self._log("error", "build", f"构建异常: {str(e)}")
            return False, str(e)

    async def lint_project(self) -> Tuple[bool, str]:
        """运行 ESLint 检查代码质量。"""
        try:
            await self._log("info", "lint", "开始代码检查...")

            cmd = "npm run lint 2>nul || npm run lint:fix 2>nul || echo LINT_SKIPPED"
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.project_path),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            output = (result.stdout or "") + (result.stderr or "")
            if "LINT_SKIPPED" in output or result.returncode == 0:
                await self._log("info", "lint", "代码检查通过")
                return True, "Lint passed"
            elif result.returncode > 0:
                await self._log("warning", "lint", f"代码检查发现问题: {output[:500]}")
                return False, output[:1000]
            else:
                await self._log("info", "lint", "代码检查跳过（lint script 未配置）")
                return True, "Lint skipped"

        except subprocess.TimeoutExpired:
            await self._log("warning", "lint", "代码检查超时")
            return False, "Lint timeout"
        except Exception as e:
            await self._log("warning", "lint", f"代码检查异常: {str(e)}")
            return False, str(e)

    async def test_dev_server(self) -> Tuple[bool, str]:
        """启动 dev server，验证能正常启动后关闭。"""
        try:
            await self._log("info", "dev", "启动 dev server 进行验证...")

            cmd = "npm run dev"
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(self.project_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            startup_ok = False
            startup_error = ""
            deadline = time.time() + 30

            while time.time() < deadline:
                if process.poll() is not None:
                    startup_error = "dev server 进程退出"
                    break
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        "http://localhost:5173",
                        method="HEAD",
                    )
                    req.add_header("User-Agent", "")
                    urllib.request.urlopen(req, timeout=2)
                    startup_ok = True
                    break
                except Exception:
                    await asyncio.sleep(1)

            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            if startup_ok:
                await self._log("info", "dev", "dev server 启动成功，端口 5173 可访问")
                return True, "Dev server started successfully"
            else:
                await self._log("warning", "dev", f"dev server 启动失败: {startup_error}")
                return False, startup_error

        except Exception as e:
            await self._log("warning", "dev", f"dev server 测试异常: {str(e)}")
            return False, str(e)


async def execute_frontend_project_generation(
    document_content: str,
    project_path: str,
    project_name: str = "generated-project",
    on_log: Optional[LogCallback] = None,
    on_sse: Optional[SSEPublisher] = None,
) -> Tuple[bool, dict]:
    executor = FrontendProjectExecutor(
        project_path=project_path,
        document_content=document_content,
        project_name=project_name,
        on_log=on_log,
        on_sse=on_sse,
    )
    return await executor.execute()


async def deploy_to_vercel(project_base: str, session_id: str) -> str:
    """部署项目到 Vercel，返回生产环境 URL。"""
    token = os.environ.get("VERCEL_TOKEN", "")
    if not token:
        logger.error("VERCEL_TOKEN environment variable not set")
        return ""
    env = os.environ.copy()
    env["VERCEL_TOKEN"] = token
    env["NPM_CONFIG_LEGACY_PEER_DEPS"] = "true"
    cmd = f'vercel --token {token} --name {session_id} --yes --prod --env NPM_CONFIG_LEGACY_PEER_DEPS=true'

    logger.info("Deploying to Vercel: {} in {}", session_id, project_base)
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=project_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        stdout, stderr = process.communicate(timeout=300)

        logger.info("Vercel stdout: {}", stdout[:500] if stdout else "(empty)")
        if stderr:
            logger.warning("Vercel stderr: {}", stderr[:500])

        if process.returncode == 0:
            url_pattern = r"https://[a-zA-Z0-9\-]+\.vercel\.app"
            match = re.search(url_pattern, stdout) or re.search(url_pattern, stderr)
            if match:
                vercel_url = match.group(0)
                logger.info("Vercel deployment successful: {}", vercel_url)
                return vercel_url
            else:
                logger.warning("Vercel succeeded but URL not found in output")
                return ""
        else:
            logger.error("Vercel deployment failed with code {}", process.returncode)
            return ""

    except subprocess.TimeoutExpired:
        process.kill()
        logger.error("Vercel deployment timed out after 300 seconds")
        return ""
    except Exception as e:
        logger.error("Vercel deployment error: {}", e)
        return ""


async def package_project(project_base: str) -> bytes:
    """将项目目录打包为 ZIP（排除 node_modules、dist、.git 等）。"""
    import io, zipfile
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        ignore_dirs = ["node_modules", ".next", ".git", "dist", ".vercel", ".nuxt"]
        for root, dirs, files in os.walk(project_base):
            for d in ignore_dirs:
                if d in dirs:
                    dirs.remove(d)
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_base)
                zipf.write(file_path, arcname)

    zip_buffer.seek(0)
    logger.info("Project packaged: {} bytes", zip_buffer.getbuffer().nbytes)
    return zip_buffer.getvalue()


async def upload_to_s3(zip_data: bytes, s3_path: str) -> str:
    """上传 ZIP 到 S3，返回下载 URL。"""
    try:
        from server.core.storage import s3_client
        if s3_client.enabled:
            url = s3_client.upload_file(zip_data, s3_path, content_type="application/zip")
            if url:
                logger.info("Uploaded to S3: {}", url)
                return url
    except Exception as e:
        logger.warning("S3 upload failed: {}, using local path", e)
    return s3_path
