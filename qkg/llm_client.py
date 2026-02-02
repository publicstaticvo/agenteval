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


class AsyncLLMClient:

    PROMPT: str = ""
    SCHEMA: dict = {}

    def __init__(self, info: LLMServerInfo, sampling_params: dict, timeout: int = 600):
        self.url = f"{info.base_url.rstrip('/')}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {info.api_key}",
            "Content-Type": "application/json"
        }
        self.sampling_params = sampling_params
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
            print("LLMFunctino", type(e), str(e))
            # if isinstance(e, aiohttp.ClientResponseError) and e.status == 400: print(payload)
            raise
        
    def _availability(self, response, context):
        text = extract_json(response)
        jsonschema.validate(text, self.SCHEMA)
        return text
    
    def _organize_inputs(self, inputs: dict):
        return [{"role": "user", "content": self.PROMPT.format(**inputs)}], {}

    async def call(self, messages: list = [], inputs: dict = {}, context: dict = {}, **kwargs) -> dict | None:
        if not messages:
            messages, new_context = self._organize_inputs(inputs)
            context = {**context, **new_context}
        for x in messages:
            x['content'] = unicodedata.normalize("NFKC", x['content'])
        payload = {"model": self.model, "messages": messages, **self.sampling_params} | kwargs
        return await self._post(payload, context)


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        assert text, response
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

    KEY = 'eliminate'
    PROMPT = FILTER
    OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            result = text[self.KEY]
        except KeyError:
            print(response, text)
            raise
        if isinstance(result, str):
            if result.lower() == "true": result = True
            elif result.lower() == "false": result = False
        return result
    
    def _organize_inputs(self, inputs):
        question = f"Question: {inputs['question']}" if 'question' in inputs else ""
        options = f"Options:{''.join(f'\n{k}. {inputs['options'][k]}' for k in self.OPTIONS if k in inputs['options'])}" if 'options' in inputs else ""
        if question and options: string = f"{question}\n\n{options}"
        else: string = question or options
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': string}], {}


class Rewrite(AsyncLLMClient):

    PROMPT = REVISE
    SCHEMA = REVISE_SCHEMA
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}], {}
    

class SelfContradictFilter(Filter):
    PROMPT = SELF_CONTRADICT
    KEY = "self_contradictory"


class RedundantFilter(Filter):
    PROMPT = REDUNDANT
    KEY = "contains_redundant_information"


class ImplausibleFilter(Filter):
    PROMPT = IMPLAUSIBLE
    KEY = "physically_implausible"


class WithoutFilter(Filter):
    PROMPT = WITHOUT_QUESTION
    KEY = "judgment"


class DependsFilter(Filter):
    PROMPT = DEPENDS_ON_QUESTION
    KEY = "depends_on_question"


class Tester(AsyncLLMClient):

    OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    PROMPT = TEST

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, TEST_SCHEMA)
        return text['selected_answer']
    
    def _organize_inputs(self, inputs):
        assert len(inputs['options']) == 10, inputs
        options = {**inputs['options'], "K": "None of the above. / The question is not answerable."}
        inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {options[k]}' for k in self.OPTIONS)}"
        prompt = [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}]
        return prompt, {}
