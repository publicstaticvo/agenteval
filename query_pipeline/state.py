from typing import List, Dict, Annotated, Any
from operator import add
from pydantic import BaseModel, Field


class GeneratePayload(BaseModel):
    query: str
    query_id: int
    paper_id: int
    paper: str
    artifact: Dict[str, Any]


class GenerateState(BaseModel):
    query: str
    query_id: int
    paper_id: int
    paper: str
    artifact: Dict[str, Any]
    generated: str = ""
    tools_used: List = Field(default_factory=list)
    results: Annotated[List[Dict], add]