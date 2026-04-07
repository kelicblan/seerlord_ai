import asyncio
import json
import os
import platform
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from loguru import logger

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class VerificationLevel(Enum):
    BASIC = "basic"
    MOCK_DATA = "mock_data"
    BUILD = "build"
    RUNTIME = "runtime"


@dataclass
class VerificationResult:
    success: bool
    level: VerificationLevel
    message: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectVerifier:
    """执行项目基础、构建与运行时验证。"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.results: List[VerificationResult] = []

    async def verify_all(
        self,
        coverage_baseline: Optional[Dict[str, Any]] = None,
        levels: Optional[List[VerificationLevel]] = None
    ) -> VerificationResult:
        if levels is None:
            levels = [
                VerificationLevel.BASIC,
                VerificationLevel.MOCK_DATA,
                VerificationLevel.BUILD,
            ]
        
        all_errors = []
        all_warnings = []
        
        for level in levels:
            result = await self._verify_level(level, coverage_baseline)
            self.results.append(result)
            
            if not result.success:
                all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        overall_success = all(r.success for r in self.results)
        
        return VerificationResult(
            success=overall_success,
            level=VerificationLevel.BUILD,
            message="All verifications passed" if overall_success else "Some verifications failed",
            errors=all_errors,
            warnings=all_warnings,
        )

    async def _verify_level(
        self,
        level: VerificationLevel,
        coverage_baseline: Optional[Dict[str, Any]]
    ) -> VerificationResult:
        if level == VerificationLevel.BASIC:
            return await self._verify_basic()
        elif level == VerificationLevel.MOCK_DATA:
            return await self._verify_mock_data()
        elif level == VerificationLevel.BUILD:
            return await self._verify_build()
        elif level == VerificationLevel.RUNTIME:
            return await self._verify_runtime()
        else:
            return VerificationResult(
                success=False,
                level=level,
                message=f"Unknown verification level: {level}",
            )

    async def _verify_basic(self) -> VerificationResult:
        errors = []
        warnings = []
        
        required_files = [
            "package.json",
            "vite.config.ts",
            "tsconfig.json",
            "index.html",
            "src/main.ts",
            "src/App.vue",
        ]
        
        for file_path in required_files:
            full_path = self.project_path / file_path
            if not full_path.exists():
                errors.append(f"Missing required file: {file_path}")
        
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                
                if "scripts" not in pkg:
                    errors.append("package.json missing 'scripts' field")
                
                if "dev" not in pkg.get("scripts", {}):
                    errors.append("package.json missing 'dev' script")
                
                if "build" not in pkg.get("scripts", {}):
                    errors.append("package.json missing 'build' script")
                    
            except json.JSONDecodeError as e:
                errors.append(f"Invalid package.json: {str(e)}")
        
        return VerificationResult(
            success=len(errors) == 0,
            level=VerificationLevel.BASIC,
            message="Basic verification passed" if len(errors) == 0 else "Basic verification failed",
            errors=errors,
            warnings=warnings,
        )

    async def _verify_mock_data(self) -> VerificationResult:
        errors = []
        warnings = []
        
        mock_dirs = [
            self.project_path / "src" / "api",
            self.project_path / "src" / "mock",
            self.project_path / "src" / "mocks",
            self.project_path / "api",
        ]
        
        mock_dir = None
        for d in mock_dirs:
            if d.exists() and d.is_dir():
                mock_dir = d
                break
        
        if mock_dir is None:
            errors.append("No mock directory found (src/api, src/mocks, or api)")
            return VerificationResult(
                success=False,
                level=VerificationLevel.MOCK_DATA,
                message="Mock data verification failed",
                errors=errors,
                warnings=warnings,
            )
        
        mock_files = list(mock_dir.glob("*.ts"))
        if not mock_files:
            errors.append(f"No TypeScript mock files found in {mock_dir}")
        
        placeholder_patterns = ["test1", "test2", "xxx", "yyy", "placeholder", "todo"]
        
        for mock_file in mock_files:
            if mock_file.name in {"index.ts", "http.ts", "client.ts"}:
                continue
            
            try:
                content = mock_file.read_text(encoding="utf-8")
                
                for pattern in placeholder_patterns:
                    if pattern in content.lower():
                        warnings.append(f"{mock_file.name} contains placeholder: {pattern}")
                
                if len(content) < 100:
                    warnings.append(f"{mock_file.name} seems to be empty or too small")
                    
            except Exception as e:
                errors.append(f"Failed to read {mock_file.name}: {str(e)}")
        
        return VerificationResult(
            success=len(errors) == 0,
            level=VerificationLevel.MOCK_DATA,
            message="Mock data verification passed" if len(errors) == 0 else "Mock data verification failed",
            errors=errors,
            warnings=warnings,
        )

    async def _verify_build(self) -> VerificationResult:
        errors = []
        warnings = []
        
        if not (self.project_path / "package.json").exists():
            return VerificationResult(
                success=False,
                level=VerificationLevel.BUILD,
                message="package.json not found",
                errors=["package.json not found"],
            )
        
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "eresolve" in stderr:
                    errors.append("[INSTALL_ERESOLVE] npm peer dependency conflict")
                elif "e404" in stderr:
                    errors.append("[INSTALL_E404] npm package not found")
                elif "etarget" in stderr:
                    errors.append("[INSTALL_ETARGET] npm version not found")
                else:
                    errors.append(f"[INSTALL_FAILED] {result.stderr[:500]}")
                    
        except subprocess.TimeoutExpired:
            errors.append("[INSTALL_FAILED] npm install timeout")
        except FileNotFoundError:
            errors.append("[INSTALL_FAILED] npm not found")
        except Exception as e:
            errors.append(f"[INSTALL_FAILED] {str(e)}")
        
        if errors:
            return VerificationResult(
                success=False,
                level=VerificationLevel.BUILD,
                message="Build verification failed",
                errors=errors,
                warnings=warnings,
            )
        
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                stderr = result.stderr.lower()
                stdout = result.stdout.lower()
                
                if "tsc" in stderr or "tsc" in stdout:
                    errors.append("[BUILD_TSC] TypeScript compilation error")
                elif "vite" in stderr:
                    errors.append("[BUILD_VITE] Vite build error")
                else:
                    errors.append(f"[BUILD_FAILED] {result.stderr[:500]}")
                    
        except subprocess.TimeoutExpired:
            errors.append("[BUILD_TIMEOUT] Build timeout")
        except Exception as e:
            errors.append(f"[BUILD_FAILED] {str(e)}")
        
        return VerificationResult(
            success=len(errors) == 0,
            level=VerificationLevel.BUILD,
            message="Build verification passed" if len(errors) == 0 else "Build verification failed",
            errors=errors,
            warnings=warnings,
        )

    async def _verify_runtime(self) -> VerificationResult:
        errors = []
        warnings = []
        
        if not PLAYWRIGHT_AVAILABLE:
            warnings.append("Playwright not available, skipping runtime verification")
            return VerificationResult(
                success=True,
                level=VerificationLevel.RUNTIME,
                message="Runtime verification skipped (Playwright not available)",
                warnings=warnings,
            )
        
        port = self._find_free_port()
        server_process = None
        
        try:
            server_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)],
                cwd=str(self.project_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            await asyncio.sleep(5)
            
            if server_process.poll() is not None:
                errors.append("[SERVER_START_FAILED] Dev server failed to start")
            else:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"http://localhost:{port}", timeout=10)
                        if response.status_code != 200:
                            errors.append(f"[SERVER_START_FAILED] Server returned {response.status_code}")
                except Exception:
                    errors.append("[SERVER_START_TIMEOUT] Could not connect to dev server")
                    
        except Exception as e:
            errors.append(f"[SERVER_START_FAILED] {str(e)}")
        finally:
            if server_process:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()
        
        return VerificationResult(
            success=len(errors) == 0,
            level=VerificationLevel.RUNTIME,
            message="Runtime verification passed" if len(errors) == 0 else "Runtime verification failed",
            errors=errors,
            warnings=warnings,
        )

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def get_results(self) -> List[VerificationResult]:
        return self.results
