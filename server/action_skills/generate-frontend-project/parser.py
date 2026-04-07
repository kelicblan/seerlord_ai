import json
import re
import os
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

SKILL_DIR = Path(__file__).resolve().parent

FRONTEND_DEMO_PREFIX = "frontend-demo/"
COMMON_SOURCE_DIR_PREFIXES = (
    "api/",
    "components/",
    "composables/",
    "directives/",
    "guards/",
    "stores/",
    "types/",
    "utils/",
    "views/",
)

ALLOWED_EXACT_PATHS = frozenset({
    "generated/coverage-manifest.json",
    "src/router/index.ts",
})

ALLOWED_PREFIXES = (
    "src/api/",
    "src/composables/",
    "src/components/",
    "src/directives/",
    "src/guards/",
    "src/stores/",
    "src/types/",
    "src/utils/",
    "src/views/",
    "generated/",
)

SCAFFOLD_ALLOWED_EXACT_PATHS = frozenset({
    ".gitignore",
    "README.md",
    "eslint.config.js",
    "index.html",
    "package-lock.json",
    "package.json",
    "tsconfig.app.json",
    "tsconfig.json",
    "tsconfig.node.json",
    "vite.config.ts",
    "src/App.vue",
    "src/api/http.ts",
    "src/components/ThemeToggle.vue",
    "src/constants/app.ts",
    "src/main.ts",
    "src/router/index.ts",
    "src/stores/app.ts",
    "src/style.css",
    "src/views/NotFoundView.vue",
    "src/views/WorkspaceView.vue",
    "src/vite-env.d.ts",
})

SCAFFOLD_ALLOWED_PREFIXES = (
    "public/",
    "src/assets/",
    "src/constants/",
    "src/layouts/",
)


class FileParseError(Exception):
    pass


@dataclass
class ParsedFile:
    path: str
    content: str
    is_scaffold: bool = False
    validation_error: Optional[str] = None


def _normalize_relative_path(raw_path: str) -> str:
    normalized = raw_path.strip().replace("\\", "/").lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.lower().startswith(FRONTEND_DEMO_PREFIX):
        normalized = normalized[len(FRONTEND_DEMO_PREFIX):]
    if normalized == "generated/coverage-manifest.js":
        normalized = "generated/coverage-manifest.json"
    for prefix in COMMON_SOURCE_DIR_PREFIXES:
        if normalized.startswith(prefix):
            return normalized
    if normalized.startswith("src/"):
        return normalized
    return normalized


def validate_file_path(file_path: str, is_scaffold: bool = False) -> Tuple[bool, Optional[str]]:
    normalized = _normalize_relative_path(file_path)
    
    allowed_exact = SCAFFOLD_ALLOWED_EXACT_PATHS if is_scaffold else ALLOWED_EXACT_PATHS
    allowed_prefixes = SCAFFOLD_ALLOWED_PREFIXES if is_scaffold else ALLOWED_PREFIXES
    
    if normalized in allowed_exact:
        return True, None
    
    for prefix in allowed_prefixes:
        if normalized.startswith(prefix):
            return True, None
    
    return False, f"File path '{normalized}' is not allowed"


def extract_file_content(raw_output: str, file_path: str) -> Optional[str]:
    normalized = _normalize_relative_path(file_path)
    
    patterns = [
        rf'<file\s+path=["\'](?P<path>[^"\']+)["\']\s*>.*?(?=</file>)',
        rf'<file\s+path=["\'](?P<path>[^"\']+)["\']>\s*(?P<content>.*?)\s*</file>',
        rf'```file:(?P<path>[^`\n]+)\n(?P<content>.*?)```',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, raw_output, re.DOTALL)
        for match in matches:
            matched_path = _normalize_relative_path(match.group("path"))
            if matched_path == normalized or normalized in matched_path:
                return match.group("content").strip()
    
    return None


def parse_json_output(raw_output: str) -> Dict[str, Any]:
    output = raw_output.strip()
    
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
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


def parse_generated_files(raw_output: str) -> Tuple[List[ParsedFile], List[str]]:
    files = []
    errors = []
    json_output = parse_json_output(raw_output)
    json_files = json_output.get("files", {}) if isinstance(json_output, dict) else {}
    is_scaffold = "package.json" in raw_output or "vite.config.ts" in raw_output

    if isinstance(json_files, dict) and json_files:
        for raw_path, raw_content in json_files.items():
            file_path = _normalize_relative_path(str(raw_path))
            content = str(raw_content)
            is_valid, error = validate_file_path(file_path, is_scaffold)
            files.append(
                ParsedFile(
                    path=file_path,
                    content=content,
                    is_scaffold=is_scaffold,
                    validation_error=error,
                )
            )
            if error:
                errors.append(f"{file_path}: {error}")
        if files:
            return files, errors
    
    file_patterns = [
        r'<file\s+path=["\'](?P<path>[^"\']+)["\'][^>]*>(?P<content>.*?)</file>',
        r'```file:(?P<path>[^`\n]+)\n(?P<content>.*?)```',
    ]

    
    for pattern in file_patterns:
        matches = re.finditer(pattern, raw_output, re.DOTALL)
        for match in matches:
            file_path = _normalize_relative_path(match.group("path"))
            content = match.group("content").strip()
            
            is_valid, error = validate_file_path(file_path, is_scaffold)
            
            parsed_file = ParsedFile(
                path=file_path,
                content=content,
                is_scaffold=is_scaffold,
                validation_error=error,
            )
            files.append(parsed_file)
            
            if error:
                errors.append(f"{file_path}: {error}")
    
    return files, errors


def save_parsed_files(
    files: List[ParsedFile],
    project_path: str,
    overwrite: bool = True
) -> Tuple[List[str], List[str]]:
    saved = []
    errors = []
    
    project_dir = Path(project_path)
    
    for file in files:
        if file.validation_error:
            errors.append(f"Skipped {file.path}: {file.validation_error}")
            continue
        
        file_path = project_dir / file.path
        
        if not overwrite and file_path.exists():
            errors.append(f"Skipped {file.path}: already exists")
            continue
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file.content)
            saved.append(file.path)
        except Exception as e:
            errors.append(f"Failed to save {file.path}: {str(e)}")
    
    return saved, errors


def extract_all_json_blocks(raw_output: str) -> List[Dict[str, Any]]:
    results = []
    
    json_blocks = re.findall(
        r'```json\s*(\{.*?\})\s*```',
        raw_output,
        re.DOTALL
    )
    
    for block in json_blocks:
        try:
            data = json.loads(block)
            results.append(data)
        except json.JSONDecodeError:
            continue
    
    return results


def parse_coverage_manifest(raw_output: str) -> Optional[Dict[str, Any]]:
    manifest_patterns = [
        r'coverage-manifest\.json.*?```json\s*(\{.*?\})\s*```',
        r'```json\s*(\{.*?"routesImplemented".*?\})\s*```',
    ]
    
    for pattern in manifest_patterns:
        match = re.search(pattern, raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    
    return None
