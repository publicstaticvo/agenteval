import aiohttp
import jsonschema
from tenacity import (
    retry,
    stop_after_attempt,           # 最大重试次数
    wait_exponential,             # 指数退避
    retry_if_exception,           # 遇到什么异常才重试
    retry_if_result,              # 返回None的时候也要重试
)
from abc import ABC, abstractmethod
from config import LLMServerInfo
from session_manager import SessionManager, RateLimit
from prompts import *
from utils import extract_json


def should_retry(exception: BaseException) -> bool:
    if isinstance(exception, NameError): return False
    if isinstance(exception, TypeError): return False
    if isinstance(exception, AttributeError): return False
    if isinstance(exception, KeyboardInterrupt): return False
    if isinstance(exception, NotImplementedError): return False
    return True


class AsyncLLMClient(ABC):

    PROMPT: str = ""

    def __init__(self, info: LLMServerInfo, timeout: int = 1800):
        self.url = f"{info.base_url.rstrip('/')}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {info.api_key}",
            "Content-Type": "application/json"
        }
        self.model = info.model
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception(should_retry)
    )
    async def _post(self, payload: dict, context: dict) -> dict:
        try:
            async with RateLimit.LLM_SEMAPHORE:
                async with SessionManager.get().post(self.url, json=payload, headers=self.headers,
                                                     timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._availability(content, context)
        except Exception as e:
            print(type(e), e)
            raise
        
    @abstractmethod
    def _availability(self, response, context):
        raise NotImplementedError
    
    def _organize_inputs(self, inputs: dict):
        return [{"role": "user", "content": self.PROMPT.format(**inputs)}], {}

    async def call(self, messages: list = [], inputs: dict = {}, context: dict = {}, **kwargs) -> dict | None:
        if not messages:
            messages, new_context = self._organize_inputs(inputs)
            context = {**context, **new_context}
        payload = {"model": self.model, "messages": messages, "temperature": 0.0, "max_tokens": 4096} | kwargs
        return await self._post(payload, context)


class Step1(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        x = extract_json(response)
        return context['inputs'] if x['extractable'] else {}


class ExtractStep(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        results = extract_json(response)
        if not results: return {}
        jsonschema.validate(results, STEP_2_SCHEMA)
        for x in results["evidence"]['text_anchor']:
            x = x.split('.')
            for z in x: assert z.lower() in context['inputs']['text'].lower()
        return results
    
    def _organize_inputs(self, inputs):
        prompt = STEP_1_USER.format(**inputs)
        return [{'role': 'system', 'content': STEP_12}, {'role': 'user', 'content': prompt}], {"inputs": inputs}
    

class ValidStep(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        try:
            x = extract_json(response)
            return context['inputs'] if x['fully_supported'] else {}
        except Exception as e:
            print(e)
    
    def _organize_inputs(self, inputs):
        # anchors = "\n".join(f"- {x}" for x in inputs['evidence']['text_anchor'])
        prompt = STEP_3_USER.format(claim=inputs['claim'], text=" ".join(inputs['evidence']['text_anchor']))
        return [{'role': 'system', 'content': STEP_3}, {'role': 'user', 'content': prompt}], {"inputs": inputs}  
