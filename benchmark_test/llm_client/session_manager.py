import asyncio, aiohttp
from typing import Optional

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}


class RateLimit:
    LLM_SEMAPHORE = asyncio.Semaphore(50)       # LLM


class SessionManager:
    _global_session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def init(cls):
        """进入上下文时调用"""
        if cls._global_session is None:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=50, ttl_dns_cache=300)
            cls._global_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    @classmethod
    async def close(cls):
        """退出上下文时调用"""
        if cls._global_session and not cls._global_session.closed:
            await cls._global_session.close()
            cls._global_session = None
    
    @classmethod
    def get(cls) -> aiohttp.ClientSession:
        """获取全局 session"""
        if cls._global_session is None:
            raise RuntimeError("SessionManager not initialized")
        return cls._global_session
