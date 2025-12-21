import yaml
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import os

class AgentConfig(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[str] = Field(default_factory=list)
    verbose: bool = True
    allow_delegation: bool = False
    llm_config: Optional[Dict[str, Any]] = None

class TaskConfig(BaseModel):
    id: str
    description: str
    expected_output: str
    agent: str
    context: List[str] = Field(default_factory=list)
    async_execution: bool = False

class ConfigLoader:
    @staticmethod
    def load_agents(path: str) -> Dict[str, AgentConfig]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent config not found at {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        agents = {}
        if "agents" in data:
            for name, config in data["agents"].items():
                agents[name] = AgentConfig(**config)
        return agents

    @staticmethod
    def load_tasks(path: str) -> List[TaskConfig]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Task config not found at {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        tasks = []
        if "tasks" in data:
            for task_data in data["tasks"]:
                tasks.append(TaskConfig(**task_data))
        return tasks
