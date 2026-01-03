# -----------------------------------------------------------------------------
# File: llm/stores/redis_episodic_store.py
# -----------------------------------------------------------------------------

import json
import time
from typing import Any, Dict, List, Optional
import redis.asyncio as redis

from llm.stores.base import EpisodicStore


class RedisEpisodicStore(EpisodicStore):
    """
    Episodic memory store backed by Redis (no RedisSearch).
    """

    def __init__(self, url: str):
        self.redis = redis.from_url(url)
        self.prefix = "episode:"

    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ):
        data = json.dumps(value)
        k = f"{self.prefix}{key}"
        await self.redis.set(k, data)
        if ttl_seconds:
            await self.redis.expire(k, ttl_seconds)

    async def fetch(
        self,
        key: Optional[str] = None,
        limit: int = 10,
    ):
        if key:
            data = await self.redis.get(f"{self.prefix}{key}")
            return [json.loads(data)] if data else []

        keys = await self.redis.keys(f"{self.prefix}*")
        results = []
        for k in keys[:limit]:
            data = await self.redis.get(k)
            if data:
                results.append(json.loads(data))
        return results

    async def delete(self, key: str):
        await self.redis.delete(f"{self.prefix}{key}")

    async def clear(self):
        keys = await self.redis.keys(f"{self.prefix}*")
        if keys:
            await self.redis.delete(*keys)

