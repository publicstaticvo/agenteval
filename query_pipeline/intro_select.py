from typing import List, Dict, Any
from tenacity import RetryError

from prompts import *
from state import GenerateState
from config import LLMServerInfo
from llm_client import AsyncLLMClient
from utils import skeleton_to_list, extract_json


class AsyncSelectClient(AsyncLLMClient):
    def _availability(self, response: str):
        num_paragraphs = self._context.get("num_paragraphs", 0)
        if num_paragraphs <= 0:
            raise ValueError("You should pass num_paragraphs to Select LLM Client")
        response = extract_json(response)
        goal, recipe = response['goal_paragraph_indexes'], response['recipe_paragraph_indexes']
        assert all(1 <= i <= num_paragraphs for i in goal + recipe), (goal, recipe, num_paragraphs)
        return goal + recipe


class SelectNode:
    def __init__(self, llm: LLMServerInfo):
        self.client = AsyncSelectClient(llm)

    async def __call__(self, state: GenerateState) -> Dict[str, List[Dict[str, Any]]]:
        print(f"Select paper range for query {state.query_id} paper id {state.paper_id} title {state.paper['title']}")
        paper = state.paper
        content, paragraphs = skeleton_to_list(paper['structure'])
        user_message = SELECT_USER.format(title=paper['title'], abstract=paper['abstract'], text=content)
        messages = [
            {"role": "system", "content": SELECT_SYSTEM},
            {"role": "user", "content": user_message},
        ]
        try:
            target = await self.client.call(messages, temperature=0, max_tokens=1024, context={"num_paragraphs": len(paragraphs)})
            if target is None:
                return {"sections": ""}
            return {"sections": "\n\n".join(paragraphs[i - 1] for i in target)}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if isinstance(e, RetryError): print(f"SelectNode {e.last_attempt.result()}")
            else: print(f"SelectNode {e}")