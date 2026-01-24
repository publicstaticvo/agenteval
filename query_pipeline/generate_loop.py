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
        return response, response['new_research_query'], response['required_tools'], response['probe_spec']['probe_dimensions']


class GenerateNode:

    def __init__(self, llm: LLMServerInfo, tools_desc: str):
        self.client = AsyncGenerateClient(llm)
        self.tools = tools_desc

    async def __call__(self, state: GenerateState) -> dict | None:
        if state.results:
            messages = [
                {"role": "system", "content": REVISE_SYSTEM},
                {"role": "user", "content": REVISE_USER.format(
                    tools=self.tools, 
                    text=state.artifact, 
                    query=state.results[-1]['optimized'], 
                    critic=json.dumps(state.results[-1]['critic'], ensure_ascii=False, indent=2)
                )}
            ]  
        else:
            messages = [
                {"role": "system", "content": GENERATE_SYSTEM},
                {"role": "user", "content": GENERATE_USER.format(tools=self.tools, text=state.artifact)}
            ]     
        try:
            generated = await self.client.call(messages, temperature=0.8)
            return {"generated": generated}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if isinstance(e, RetryError): print(f"GenerateNode {e.last_attempt.result()}")
            else: print(f"GenerateNode {e}")
            return {"generated": {}}


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
        if not state.generated: return
             
        messages = [
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user", "content": CRITIC_USER.format(
                tools=self.tools, 
                result=state.artifact['result'],
                method=state.artifact['method'],
                query=state.generated, 
                num_tools=len(state.generated['required_tools']),
                tools_used=', '.join(state.generated['required_tools']) if state.generated['required_tools'] else 'No'
            )}
        ]
        try:
            critic = await self.client.call(messages, temperature=0)
            return {"critics": critic}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if isinstance(e, RetryError): print(f"CriticNode {e.last_attempt.result()}")
            else: print(f"CriticNode {e}")
