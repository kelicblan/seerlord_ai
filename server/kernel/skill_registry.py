import importlib
import inspect
from typing import Dict
from pathlib import Path
import sys
from loguru import logger
from langchain_core.tools import BaseTool
from server.core.config import settings

class SkillRegistry:
    """
    Registry for Skills (LangChain Tools).
    Allows automatic scanning and loading of skills from 'server/skills'.
    """
    _instance = None
    _skills: Dict[str, BaseTool] = {}
    _loaded_modules: set = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
        return cls._instance

    @property
    def skills(self) -> Dict[str, BaseTool]:
        return self._skills

    def register(self, skill: BaseTool):
        if skill.name in self._skills:
            logger.warning(f"Skill {skill.name} already registered. Overwriting.")
        self._skills[skill.name] = skill
        logger.info(f"Registered Skill: {skill.name}")

    def scan_and_load(self):
        """
        Scans 'server/skills' directory and loads all BaseTool instances.
        """
        # Assume skills are in server/skills
        # We need to calculate absolute path relative to project root
        project_root = Path.cwd()
        skills_path = project_root / "server" / "skills"
        
        if not skills_path.exists():
            logger.warning(f"Skills directory does not exist: {skills_path}")
            return

        logger.info(f"Scanning skills directory: {skills_path}")
        
        # Ensure project root is in sys.path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        base_package = "server.skills"
        
        for item in skills_path.iterdir():
            if item.name.startswith("_") or item.name.startswith("."):
                continue

            module_name = ""
            if item.is_file() and item.suffix == ".py":
                module_name = f"{base_package}.{item.stem}"
            elif item.is_dir():
                module_name = f"{base_package}.{item.name}"
            
            if not module_name:
                continue

            if module_name in self._loaded_modules:
                continue

            try:
                logger.debug(f"Loading skill module: {module_name}")
                module = importlib.import_module(module_name)
                self._register_skills_from_module(module)
                self._loaded_modules.add(module_name)
            except Exception as e:
                logger.error(f"Failed to load skill module {module_name}: {e}")

    def _register_skills_from_module(self, module):
        """
        Finds BaseTool subclasses or instances in the module.
        """
        # Check for BaseTool instances directly
        for name, obj in inspect.getmembers(module):
            if isinstance(obj, BaseTool):
                self.register(obj)
            # Also check for classes that are BaseTool but not BaseTool itself
            # And instantiate them if they have no required init args
            elif (inspect.isclass(obj) and 
                  issubclass(obj, BaseTool) and 
                  obj is not BaseTool):
                try:
                    # Try to instantiate with no args
                    instance = obj()
                    self.register(instance)
                except TypeError:
                    # Might require arguments, skip automatic instantiation
                    logger.debug(f"Skipping {name}: requires initialization arguments.")

skill_registry = SkillRegistry()
