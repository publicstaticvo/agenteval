import json
from typing import List, Dict, Optional, Any

from prompts import *
from state import GenerateState
from config import LLMServerInfo
from session_manager import RateLimit
from llm_client import AsyncLLMClient
from utils import skeleton_to_list, extract_json


class AsyncSelectClient(AsyncLLMClient):
    def _availability(self, response: str):
        response = extract_json(response)
        return response['goal_paragraph_indexes'], response['recipe_paragraph_indexes']


class SelectNode:
    def __init__(self, llm: LLMServerInfo):
        self.client = AsyncSelectClient(llm)

    async def __call__(self, state: GenerateState) -> Dict[str, List[Dict[str, Any]]]:
        async with RateLimit.SELECT_GENERATE_SEMAPHORE:
            paper = state.paper
            content, paragraphs = skeleton_to_list(paper['structure'])
            user_message = SELECT_USER.format(title=paper['title'], abstract=paper['abstract'], text=content)
            messages = [
                {"role": "system", "content": SELECT_SYSTEM},
                {"role": "user", "content": user_message},
            ]
            goal, recipe = await self.client.call(messages)
            return {"sections": "\n\n".join(paragraphs[i] for i in goal + recipe)}


class AsyncGenerateClient(AsyncLLMClient):
    def _availability(self, response: str):
        response = extract_json(response)
        return response['optimized_query'], response['tools_required']


class GenerateNode:

    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncGenerateClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> dict | None:
        """生成工具感知的优化查询 - 必须使用 3 个工具"""
        # 每轮都要设置当前查询，因为可能从 output_node 循环回来。
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
                generated, tools_used = await self.client.call(messages, 0.6, 4096)
                print(f"query {state.query_id} iteration {len(state.results) + 1}")
                return {"generated": generated, "tools_used": tools_used}
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"GenerateNode {e}")


class AsyncCriticClient(AsyncLLMClient):
    def _availability(self, response: str):
        response = extract_json(response)
        score = response.get('total_score')
        if isinstance(score, str) and score.isdigit():
            response['total_score'] = int(score)
        return response


class CriticNode:
    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncGenerateClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> Optional[Dict]:
        """严格的学术评分 - 工具利用比重提升"""
        tools_used = state.get("tools_used", [])
        generated = state.get("generated", "")    
        if not generated: return
        
        async with RateLimit.CRITIC_SEMAPHORE:
            user = CRITIC_USER.format(
                tools_info=self.tools, 
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
                print(f"CriticNode {e}")
