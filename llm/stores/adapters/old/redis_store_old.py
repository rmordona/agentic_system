import json
import redis.asyncio as redis
import numpy as np
from langgraph.store.base import BaseStore
from llm.stores.store_factory import StoreFactory

class RedisStore(BaseStore):
    def __init__(
        self,
        url: str,
        index: str = "memory_idx",
        dim: int = 1536,
    ):
        self.redis = redis.from_url(url)
        self.index = index
        self.dim = dim

    async def put(self, key, value, *, namespace=None):
        redis_key = f"memory:{namespace}:{key}"
        await self.redis.hset(
            redis_key,
            mapping={
                "payload": json.dumps(value["data"]),
                "embedding": np.array(value["embedding"], dtype=np.float32).tobytes(),
            },
        )

    async def get(self, key, *, namespace=None):
        redis_key = f"memory:{namespace}:{key}"
        data = await self.redis.hget(redis_key, "payload")
        return json.loads(data) if data else None

    async def search(self, query_vector, *, namespace=None, top_k=5):
        q = (
            f"*=>[KNN {top_k} @embedding $vec "
            f"AS score]"
        )

        results = await self.redis.ft(self.index).search(
            q,
            query_params={
                "vec": np.array(query_vector, dtype=np.float32).tobytes()
            },
        )

        return [
            json.loads(doc.payload)
            for doc in results.docs
        ]


# register dynamically
StoreFactory.register("postgres", RedisVectorStore)
