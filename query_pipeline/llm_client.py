import aiohttp
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
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception(should_retry) | retry_if_result(lambda x: x is None)
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
        