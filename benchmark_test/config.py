import yaml
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMServerInfo:
    base_url: str
    api_key: str | None = None
    model: str = "whatever"
    

@dataclass(frozen=True)
class Config:
    test_input: str = "workflow.jsonl"
    answer_output: str = "workflow.jsonl"
    models: list[LLMServerInfo] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, config_path):
        with open(config_path, encoding='utf-8') as f: config = yaml.safe_load(f)
        return cls(
            test_input=config['test_input'],
            answer_output=config['answer_output'],
            models=[LLMServerInfo(**c) for c in config['models']],
        )
