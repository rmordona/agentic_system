import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import redis.asyncio as aioredis
from runtime.memory_schemas import BaseModel
from runtime.memory_adapters.base import MemoryAdapter


class RedisEpisodicAdapter(MemoryAdapter):

    def __init__(self, config: dict):
        self.redis_url = config.get("url", "redis://localhost:6379/0")
        self.namespace = config.get("namespace", "episodic")
        self.ttl_seconds = config.get("ttl_seconds")

        self.redis = aioredis.from_url(self.redis_url)

    def _key(self, session_id: str, uid: str):
            return f"{self.namespace}:{session_id}:{uid}"

    async def store_memory(self, memory: BaseModel) -> str:
        """
        Stores a memory object in Redis. Returns the generated key.
        """
        key = str(uuid4())
        redis_key = self._key(memory.session_id, key)

        await self.redis.set(
            redis_key,
            memory.model_dump_json(),
            ex=self.ttl_seconds,  # 👈 TTL HERE
        )
        return redis_key


    async def fetch_memory(
        self,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        *,
        top_k: Optional[int] = 5,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch stored memories filtered by task, agent, or stage.
        Returns list of memory dicts.
        """
        keys = await self.redis.keys(f"{self.namespace}:{session_id}:*")
        results = []

        for key in keys:
            raw = await self.redis.get(key)
            if not raw:
                continue
            memory = json.loads(raw)

            # ---- Session Filter
            if session_id and memory.get("session_id") != session_id:
                continue

            # Filtering
            if task and memory.get("task") != task:
                continue
            if agent:
                if isinstance(agent, str) and memory.get("agent") != agent:
                    continue
                if isinstance(agent, list) and memory.get("agent") not in agent:
                    continue
            if stage:
                if isinstance(stage, str) and memory.get("stage") != stage:
                    continue
                if isinstance(stage, list) and memory.get("stage") not in stage:
                    continue

            results.append(memory)

        return results

    async def clear(self):
        """Delete all keys in this namespace."""
        keys = await self.redis.keys(f"{self.namespace}:*")
        if keys:
            await self.redis.delete(*keys)


    
