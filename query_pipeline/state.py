from typing import List, Dict, Annotated, Any, NotRequired
from operator import add
from typing_extensions import TypedDict
from paper_elements import Paragraph


class InputState(TypedDict):
    query_id: int
    query: str          # 另一种实现：query_list做输入，Send分发到search


class AgentState(TypedDict):
    query_id: int
    query: str
    retrieved_papers: List[Dict[str, Any]]


class GeneratePayload(TypedDict):
    query: str
    query_id: int
    paper_id: int
    paper: Dict[str, Any]


class GenerateState(TypedDict):
    query: str
    query_id: int
    paper_id: int
    paper: Dict[str, Any]
    sections: NotRequired[str]
    generated: NotRequired[str]
    tools_used: NotRequired[List]
    results: Annotated[List[Dict], add]