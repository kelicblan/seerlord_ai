"""基础设施生成器：负责复制稳定模板，或在模板不可用时生成最小脚手架。"""
import shutil
from pathlib import Path
from typing import Dict

from .base import BaseGenerator, GenerationResult, GenerationContext
from .scaffold import ScaffoldGenerator
from ..memory.short_term import ShortTermMemory


class InfrastructureGenerator(BaseGenerator):
    """复制稳定模板或生成最小基础脚手架。"""

    def __init__(self, template_path: str = None):
        super().__init__()
        self.template_path = template_path
        self._resolved_template_path: Path = None
        
    def _get_template_path(self) -> Path:
        """解析模板路径，优先使用构造函数传入的路径，否则自动定位 skill 目录下的模板。"""
        if self._resolved_template_path:
            return self._resolved_template_path
            
        if self.template_path:
            path = Path(self.template_path)
        else:
            skill_dir = Path(__file__).resolve().parents[3] / "action_skills" / "generate-frontend-project" / "template"
            path = skill_dir
            
        if not path.exists():
            base_dir = Path(__file__).resolve().parents[3]
            alt_path = base_dir / "action_skills" / "generate-frontend-project" / "template"
            if alt_path.exists():
                path = alt_path
                
        self._resolved_template_path = path
        return path

    async def generate(
        self,
        session: ShortTermMemory,
        context: GenerationContext,
    ) -> GenerationResult:
        """生成基础设施：优先复制真实模板，回退到 ScaffoldGenerator 生成最小脚手架。"""
        try:
            template_path = self._get_template_path()
            
            if template_path.exists():
                files = self._copy_template(context.project_path, template_path)
                source = "template"
            else:
                files = ScaffoldGenerator().generate_all()
                source = "generated"
            
            saved_files = self._save_files(files, context.project_path)
            
            return GenerationResult(
                success=True,
                files_generated=saved_files,
                files_content=files,
                metadata={
                    "source": source,
                    "template_path": str(template_path),
                },
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=str(e),
            )

    def _copy_template(self, project_path: str, template_path: Path) -> Dict[str, str]:
        """将模板目录中的所有文件复制到目标项目路径，返回文件路径与内容的映射。"""
        files = {}
        project_path = Path(project_path)
        skip_dirs = {"examples", ".git", "node_modules", "dist", ".vercel"}

        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                if any(part in skip_dirs for part in file_path.parts):
                    continue
                rel_path = file_path.relative_to(template_path)
                dest_path = project_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                try:
                    files[str(rel_path)] = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    files[str(rel_path)] = ""

        return files
