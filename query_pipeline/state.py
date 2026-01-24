from typing import List, Dict, Annotated, Any
from operator import add
from pydantic import BaseModel, Field


class GenerateState(BaseModel):
    query: str
    query_id: int
    paper_id: int
    paper: str
    artifact: str
    generated: Dict[str, Any] = Field(default_factory=dict)
    critics: Dict[str, Any] = Field(default_factory=dict)
    results: Annotated[List, add]
