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
from utils import extract_json
from session_manager import SessionManager


def should_retry(exception: BaseException) -> bool:
    if isinstance(exception, KeyboardInterrupt): return False
    if isinstance(exception, NotImplementedError): return False
    return True


class AsyncLLMClient(ABC):
    def __init__(self, info: LLMServerInfo, timeout: int = 600):
        self.url = f"{info.base_url.rstrip('/')}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {info.api_key}",
            "Content-Type": "application/json"
        }
        self.model = info.model
        self.timeout = timeout

    async def _post(self, session: aiohttp.ClientSession, payload: dict) -> dict:
        async with session.post(self.url, json=payload, headers=self.headers,
                                timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
            resp.raise_for_status()
            return await resp.json()
        
    @abstractmethod
    def _availability(self, response):
        raise NotImplementedError

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception(should_retry) | retry_if_result(lambda x: x is None)
    )
    async def call(self, messages: list, temperature: float = 0.6, max_tokens: int = 1024, **kwargs) -> dict | None:
        self._context = kwargs  
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }      
        session = SessionManager.get()        
        data = await self._post(session, payload)
        content = data["choices"][0]["message"]["content"]
        return self._availability(content)