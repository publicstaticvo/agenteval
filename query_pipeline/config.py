import os
import json
import yaml
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Mapping
from datetime import datetime


@dataclass(frozen=True)
class LLMServerInfo:
    base_url: str
    api_key: str | None = None
    model: str = "whatever"
    

@dataclass(frozen=True)
class Config:
    input_file: list[str] = []
    tool_file: str = "tools.json"
    n_queries: int = 5
    domain: str = "科研数据处理"
    model: str = "whatever"
    first_output: str = "first.json"
    workflow_output: str = "workflow.json"

    @classmethod
    def from_yaml(cls, config_path):
        if not os.path.exists(config_path): return cls()
        with open(config_path) as f: config = yaml.safe_load(f)
        return cls(
            input_file=config['input_file'],
            tool_file=config['tool_file'],
            n_queries=config['n_queries'],
            domain=config['domain'],
            model=config['model'],
            first_output=config['first_output'],
            workflow_output=config['workflow_output'],
        )
    
    def __str__(self):
        return self.__dict__