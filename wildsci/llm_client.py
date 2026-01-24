import re
import json
import aiohttp
import jsonschema
import unicodedata
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

    def __init__(self, info: LLMServerInfo, timeout: int = 600):
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
                body = json.dumps(payload).encode("utf-8")
                async with SessionManager.get().post(self.url, data=body, headers=self.headers,
                                                     timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._availability(content, context)
        except Exception as e:
            print("LLMFunctino", type(e))
            if isinstance(e, aiohttp.ClientResponseError) and e.status == 400: print(payload)
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
        for x in messages:
            x['content'] = unicodedata.normalize("NFKC", x['content'])
        payload = {"model": self.model, "messages": messages, "temperature": 0.8, "max_tokens": 4096} | kwargs
        return await self._post(payload, context)


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, GENERATE_SCHEMA)
        questions = []
        # 预过滤
        STOP_WORDS = ['fig.', 'tbl.', 'see fig', 'shown in fig', 
                      'see section', 'this section', 'sec.', 'appendix', 'eq.', 'the paper', 'this paper']
        for x in text['questions']:
            if any(y in x['question'].lower() for y in STOP_WORDS): continue
            questions.append(x)
        return questions
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': inputs}], {}
    

class Filter(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        response = extract_json(response)
        return response['eliminate']
    
    def _organize_inputs(self, inputs):
        inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {inputs['options'][k]}' for k in ['A', 'B', 'C', 'D'])}"
        return [{'role': 'system', 'content': FILTER}, {'role': 'user', 'content': inputs}], {}


class Rewrite(AsyncLLMClient):

    PROMPT = REVISE

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, REVISE_SCHEMA)
        return text
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': REVISE}, {'role': 'user', 'content': inputs}], {}
    

class Tester(AsyncLLMClient):

    OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    PROMPT = TEST

    def _availability(self, response: str, context: dict):
        results = re.findall(r"\\boxed\{(?:([A-K]))\}", response)[-1]
        # answer = ""
        # for r in results:
        #     r = r.lower().replace("option", "").replace("\\text{", "").replace("}", "").strip().upper()
        #     if r in self.OPTIONS: answer = r
        # assert answer
        return self.model, results
    
    def _organize_inputs(self, inputs):
        assert len(inputs['options']) == 10, inputs
        options = {**inputs['options'], "K": "None of the above. / The question is not answerable."}
        inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {options[k]}' for k in self.OPTIONS)}"
        prompt = [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}]
        return prompt, {}


class ScientificSignificance(AsyncLLMClient):

    PROMPT = SCIENTIFIC_SIGNIFICANCE

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, REVISE_SCHEMA)
        return text
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': REVISE}, {'role': 'user', 'content': inputs}], {}


class Critic(Tester):

    PROMPT = CRITIC

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            jsonschema.validate(text, CRITIC_SCHEMA)
        except Exception as e:
            print(response)
        return self.model, text
