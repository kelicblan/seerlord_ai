import os
import json
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ErrorSolution(BaseModel):
    id: str
    keywords: List[str] = Field(default_factory=list)
    root_cause: str
    solutions: List[Dict[str, Any]] = Field(default_factory=list)
    success_rate: float = 0.0
    last_updated: float = Field(default_factory=time.time)


class GenerationTechnique(BaseModel):
    id: str
    task_type: str
    effective_pattern: str
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: float = Field(default_factory=time.time)


class ProjectTemplate(BaseModel):
    id: str
    name: str
    tech_stack: Dict[str, str]
    file_structure: List[str]
    key_files: Dict[str, str]
    success_count: int = 0
    last_used: float = Field(default_factory=time.time)


class SuccessfulCase(BaseModel):
    id: str
    project_name: str
    document_type: str
    modules: List[str]
    key_insights: List[str] = Field(default_factory=list)
    success_rate: float = 1.0
    created_at: float = Field(default_factory=time.time)


class FailedCase(BaseModel):
    id: str
    project_name: str
    document_type: str
    error_type: str
    root_cause: str
    attempts: List[Dict[str, Any]] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class LongTermMemory:
    def __init__(self, base_path: str = "server/data/frontend_project_knowledge"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.errors_path = self.base_path / "errors"
        self.techniques_path = self.base_path / "techniques"
        self.templates_path = self.base_path / "templates"
        self.cases_path = self.base_path / "cases"
        
        for path in [self.errors_path, self.techniques_path, self.templates_path, self.cases_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        self._error_patterns: Dict[str, ErrorSolution] = {}
        self._techniques: Dict[str, GenerationTechnique] = {}
        self._templates: Dict[str, ProjectTemplate] = {}
        self._successful_cases: Dict[str, SuccessfulCase] = {}
        self._failed_cases: Dict[str, FailedCase] = {}
        
        self.load()

    def load(self) -> None:
        self._load_error_patterns()
        self._load_techniques()
        self._load_templates()
        self._load_cases()

    def save(self) -> None:
        self._save_error_patterns()
        self._save_techniques()
        self._save_templates()
        self._save_cases()

    def _load_error_patterns(self) -> None:
        error_file = self.errors_path / "patterns.json"
        if error_file.exists():
            with open(error_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("patterns", []):
                    pattern = ErrorSolution(**item)
                    self._error_patterns[pattern.id] = pattern

    def _save_error_patterns(self) -> None:
        error_file = self.errors_path / "patterns.json"
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(
                {"patterns": [p.model_dump() for p in self._error_patterns.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _load_techniques(self) -> None:
        technique_file = self.techniques_path / "techniques.json"
        if technique_file.exists():
            with open(technique_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("techniques", []):
                    technique = GenerationTechnique(**item)
                    self._techniques[technique.id] = technique

    def _save_techniques(self) -> None:
        technique_file = self.techniques_path / "techniques.json"
        with open(technique_file, "w", encoding="utf-8") as f:
            json.dump(
                {"techniques": [t.model_dump() for t in self._techniques.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _load_templates(self) -> None:
        templates_file = self.templates_path / "templates.json"
        if templates_file.exists():
            with open(templates_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("templates", []):
                    template = ProjectTemplate(**item)
                    self._templates[template.id] = template

    def _save_templates(self) -> None:
        templates_file = self.templates_path / "templates.json"
        with open(templates_file, "w", encoding="utf-8") as f:
            json.dump(
                {"templates": [t.model_dump() for t in self._templates.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _load_cases(self) -> None:
        success_file = self.cases_path / "successful.json"
        if success_file.exists():
            with open(success_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("cases", []):
                    case = SuccessfulCase(**item)
                    self._successful_cases[case.id] = case
        
        failed_file = self.cases_path / "failed.json"
        if failed_file.exists():
            with open(failed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("cases", []):
                    case = FailedCase(**item)
                    self._failed_cases[case.id] = case

    def _save_cases(self) -> None:
        success_file = self.cases_path / "successful.json"
        with open(success_file, "w", encoding="utf-8") as f:
            json.dump(
                {"cases": [c.model_dump() for c in self._successful_cases.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )
        
        failed_file = self.cases_path / "failed.json"
        with open(failed_file, "w", encoding="utf-8") as f:
            json.dump(
                {"cases": [c.model_dump() for c in self._failed_cases.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def search_error_pattern(
        self, 
        error_keywords: List[str],
        threshold: float = 0.5
    ) -> List[ErrorSolution]:
        results = []
        keywords_lower = [k.lower() for k in error_keywords]
        
        for pattern in self._error_patterns.values():
            pattern_keywords_lower = [k.lower() for k in pattern.keywords]
            match_count = sum(1 for kw in keywords_lower if any(kw in pk for pk in pattern_keywords_lower))
            if match_count > 0:
                match_rate = match_count / len(error_keywords)
                if match_rate >= threshold:
                    results.append((pattern, match_rate))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]

    def search_template(self, tech_stack: Dict[str, str]) -> Optional[ProjectTemplate]:
        best_match = None
        best_match_count = 0
        
        for template in self._templates.values():
            match_count = sum(
                1 for k, v in tech_stack.items() 
                if template.tech_stack.get(k, "").startswith(v.split(" ")[0])
            )
            if match_count > best_match_count:
                best_match_count = match_count
                best_match = template
        
        return best_match

    def search_technique(self, task_type: str) -> List[GenerationTechnique]:
        task_type_lower = task_type.lower()
        results = []
        
        for technique in self._techniques.values():
            if task_type_lower in technique.task_type.lower():
                results.append(technique)
        
        results.sort(key=lambda x: x.success_rate, reverse=True)
        return results

    def add_successful_case(self, case: SuccessfulCase) -> None:
        self._successful_cases[case.id] = case
        self.save()

    def add_failed_case(self, case: FailedCase) -> None:
        self._failed_cases[case.id] = case
        self.save()

    def add_error_pattern(self, pattern: ErrorSolution) -> None:
        self._error_patterns[pattern.id] = pattern
        self.save()

    def add_technique(self, technique: GenerationTechnique) -> None:
        self._techniques[technique.id] = technique
        self.save()

    def add_template(self, template: ProjectTemplate) -> None:
        self._templates[template.id] = template
        self.save()

    def update_error_solution(
        self,
        pattern_id: str,
        solution: Dict[str, Any],
        success: bool
    ) -> None:
        if pattern_id in self._error_patterns:
            pattern = self._error_patterns[pattern_id]
            pattern.solutions.append(solution)
            if success:
                pattern.success_rate = (
                    pattern.success_rate * 0.7 + 0.3
                )
            else:
                pattern.success_rate = pattern.success_rate * 0.9
            pattern.last_updated = time.time()
            self.save()

    def update_technique_usage(
        self,
        technique_id: str,
        success: bool
    ) -> None:
        if technique_id in self._techniques:
            technique = self._techniques[technique_id]
            technique.usage_count += 1
            if success:
                technique.success_rate = (
                    technique.success_rate * 0.8 + 0.2
                )
            technique.last_used = time.time()
            self.save()

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "error_patterns_count": len(self._error_patterns),
            "techniques_count": len(self._techniques),
            "templates_count": len(self._templates),
            "successful_cases_count": len(self._successful_cases),
            "failed_cases_count": len(self._failed_cases),
        }
