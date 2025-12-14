"""
config.py - config file
"""

import os
import yaml
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMServerInfo:
    base_url: str
    api_key: str | None = None
    model: str = "whatever"
    

@dataclass(frozen=True)
class Config:
    input_file: str = "chem.txt"
    tool_file: str = "tools.json"
    n_queries: int = 5
    critic_model: str = "whatever"
    workflow_output: str = "workflow.json"
    model: LLMServerInfo = field(default_factory=LLMServerInfo)
    critic_model: LLMServerInfo = field(default_factory=LLMServerInfo)

    @classmethod
    def from_yaml(cls, config_path):
        if not os.path.exists(config_path): return cls()
        with open(config_path, encoding='utf-8') as f: config = yaml.safe_load(f)
        return cls(
            input_file=config['input_file'],
            tool_file=config['tool_file'],
            n_queries=config['n_queries'],
            workflow_output=config['workflow_output'],
            model=LLMServerInfo(**config['model']),
            critic_model=LLMServerInfo(**config['critic_model']),
        )
