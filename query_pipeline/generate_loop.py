import json
from typing import List, Dict, Optional, Any
from tenacity import RetryError

from prompts import *
from state import GenerateState
from config import LLMServerInfo
from session_manager import RateLimit
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
        print(f"Select paper range for query {state.query} paper {state.paper['title']}")

        async with RateLimit.SELECT_GENERATE_SEMAPHORE:
            paper = state.paper
            content, paragraphs = skeleton_to_list(paper['structure'])
            user_message = SELECT_USER.format(title=paper['title'], abstract=paper['abstract'], text=content)
            messages = [
                {"role": "system", "content": SELECT_SYSTEM},
                {"role": "user", "content": user_message},
            ]
            try:
                target = await self.client.call(messages, 0, num_paragraphs=len(paragraphs))
                if target is None:
                    return {"sections": ""}
                return {"sections": "\n\n".join(paragraphs[i - 1] for i in target)}
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if isinstance(e, RetryError): print(f"SelectNode {e.last_attempt.result()}")
                else: print(f"SelectNode {e}")


class AsyncGenerateClient(AsyncLLMClient):
    def _availability(self, response: str):
        response = extract_json(response)
        return response['new_research_query'], response['required_tools']


class GenerateNode:

    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncGenerateClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> dict | None:
        """生成工具感知的优化查询 - 必须使用 3 个工具"""
        print(f"Generate query round {len(state.results) + 1} for query {state.query} paper {state.paper['title']}")
        
        async with RateLimit.SELECT_GENERATE_SEMAPHORE:
            if state.results:
                messages = [
                    {"role": "system", "content": REVISE_SYSTEM},
                    {"role": "user", "content": REVISE_USER.format(
                        tools=self.tools, 
                        text=state.sections, 
                        query=state.results[-1]['optimized'], 
                        critic=json.dumps(state.results[-1]['critic'], ensure_ascii=False, indent=2)
                    )}
                ]  
            else:
                messages = [
                    {"role": "system", "content": GENERATE_SYSTEM},
                    {"role": "user", "content": GENERATE_USER.format(tools=self.tools, text=state.sections)}
                ]                               
            # 一步到位
            try:
                generated, tools_used = await self.client.call(messages, 0.8, 4096)
                print(f"query {state.query_id} iteration {len(state.results) + 1}")
                return {"generated": generated, "tools_used": tools_used}
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if isinstance(e, RetryError): print(f"GenerateNode {e.last_attempt.result()}")
                else: print(f"GenerateNode {e}")


class AsyncCriticClient(AsyncLLMClient):
    def _availability(self, response: str):
        response_dict = extract_json(response)
        score = response_dict['total_score']
        if isinstance(score, str) and score.isdigit():
            response_dict['total_score'] = int(score)
        return response_dict


class CriticNode:
    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncCriticClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> Optional[Dict]:
        """严格的学术评分 - 工具利用比重提升"""
        tools_used = state.tools_used
        generated = state.generated
        if not generated: return

        print(f"Critique round {len(state.results) + 1} for query {state.query} paper {state.paper['title']}")
        
        async with RateLimit.CRITIC_SEMAPHORE:
            user = CRITIC_USER.format(
                tools=self.tools, 
                query=generated, 
                num_tools=len(tools_used),
                tools_used=', '.join(tools_used) if tools_used else 'No'
            )    
            messages = [
                {"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user", "content": user}
            ]
            try:
                critic = await self.client.call(messages, 0, 4096)
                print(f"critic {state.query_id} iteration {len(state.results) + 1}")
                return {"results": {
                    "optimized": generated,
                    "score": critic['total_score'],
                    "tools_used": tools_used,
                    "critic": critic,
                }}
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if isinstance(e, RetryError): print(f"CriticNode {e.last_attempt.result()}")
                else: print(f"CriticNode {e}")
