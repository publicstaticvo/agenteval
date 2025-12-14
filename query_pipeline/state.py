from typing import List, Dict, Annotated, Any
from operator import add
from pydantic import BaseModel, Field


def append_reducer(left: List[Dict], right: List | Dict | None) -> List[Dict]:
    if right is None:
        return left
    
    if isinstance(right, dict): 
        left.append(right)
        return left

    if isinstance(right, list): 
        return left + right

    return left


class GeneratePayload(BaseModel):
    query: str
    query_id: int
    paper: Dict[str, Any]


class GenerateState(BaseModel):
    query: str
    query_id: int
    paper: Dict[str, Any]
    sections: str = ""
    generated: str = ""
    tools_used: List = Field(default_factory=list)
    results: Annotated[List[Dict], append_reducer]