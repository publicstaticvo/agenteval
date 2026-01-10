import json
from typing import Dict, Optional
from tenacity import RetryError

from prompts import *
from state import GenerateState
from config import LLMServerInfo
from llm_client import AsyncLLMClient
from utils import extract_json


class AsyncGenerateClient(AsyncLLMClient):
    def _availability(self, response: str, context: dict):
        response = extract_json(response)
        return response['new_research_query'], response['required_tools']


class GenerateNode:

    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncGenerateClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> dict | None:
        """生成工具感知的优化查询 - 必须使用 3 个工具"""        
        print(f"Generate query round {len(state.results) + 1} for paper {state.paper_id}")
        if state.results:
            messages = [
                {"role": "system", "content": REVISE_SYSTEM},
                {"role": "user", "content": REVISE_USER.format(
                    tools=self.tools, 
                    result=state.artifact['result'], 
                    method=state.artifact['method'],
                    query=state.results[-1]['optimized'], 
                    critic=json.dumps(state.results[-1]['critic'], ensure_ascii=False, indent=2)
                )}
            ]                
        else:
            messages = [
                {"role": "system", "content": GENERATE_SYSTEM},
                {"role": "user", "content": GENERATE_USER.format(
                    tools=self.tools, 
                    result=state.artifact['result'],
                    method=state.artifact['method']
                )}
            ]  
        # 一步到位
        try:
            generated, tools_used = await self.client.call(messages, temperature=0.8)
            return {"generated": generated, "tools_used": tools_used}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if isinstance(e, RetryError): print(f"GenerateNode {e.last_attempt.result()}")
            else: print(f"GenerateNode {e}")


class AsyncCriticClient(AsyncLLMClient):
    def _availability(self, response: str, context: dict):
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

        print(f"Critique round {len(state.results) + 1} for query {state.query_id} paper {state.paper_id}")
        user = CRITIC_USER.format(
            tools=self.tools, 
            result=state.artifact['result'],
            method=state.artifact['method'],
            query=generated, 
            num_tools=len(tools_used),
            tools_used=', '.join(tools_used) if tools_used else 'No'
        )      
        messages = [
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user", "content": user}
        ]
        try:
            critic = await self.client.call(messages, temperature=0)
            print(f"critic {state.query_id} iteration {len(state.results) + 1}")
            return {"results": [{
                "optimized": generated,
                "score": critic['total_score'],
                "tools_used": tools_used,
                "critic": critic,
            }]}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if isinstance(e, RetryError): print(f"CriticNode {e.last_attempt.result()}")
            else: print(f"CriticNode {e}")
