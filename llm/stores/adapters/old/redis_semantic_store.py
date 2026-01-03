# -----------------------------------------------------------------------------
# File: llm/stores/redis_semantic_store.py
# -----------------------------------------------------------------------------

from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.commands.search.field import VectorField, TextField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from llm.stores.base import SemanticStore


class RedisSemanticStore(SemanticStore):
    """
    Semantic store backed by Redis Stack using RedisSearch + HNSW.
    """

    def __init__(
        self,
        url: str,
        index_name: str = "semantic_idx",
        dim: int = 768,
    ):
        self.redis = redis.from_url(url)
        self.index_name = index_name
        self.dim = dim
        self.prefix = "semantic:"

    async def initialize(self):
        try:
            await self.redis.ft(self.index_name).info()
        except Exception:
            schema = (
                TextField("text"),
                TagField("key"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.dim,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            await self.redis.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[self.prefix], index_type=IndexType.HASH
                ),
            )

    async def save(
        self,
        key: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ):
        doc_key = f"{self.prefix}{key}"
        payload = {
            "key": key,
            "text": text,
            "embedding": bytes(bytearray(float(x).hex() for x in embedding)),
            "metadata": json.dumps(metadata or {}),
        }
        await self.redis.hset(doc_key, mapping=payload)
        if ttl_seconds:
            await self.redis.expire(doc_key, ttl_seconds)

    async def similarity_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ):
        query = f"*=>[KNN {top_k} @embedding $vec AS score]"
        params = {"vec": bytes(bytearray(float(x).hex() for x in embedding))}
        res = await self.redis.ft(self.index_name).search(
            query,
            query_params=params,
            return_fields=["text", "metadata", "score"],
        )
        return [
            {
                "text": d.text,
                "metadata": json.loads(d.metadata),
                "score": 1 - float(d.score),
            }
            for d in res.docs
        ]

    async def delete(self, key: str):
        await self.redis.delete(f"{self.prefix}{key}")

    async def clear(self):
        keys = await self.redis.keys(f"{self.prefix}*")
        if keys:
            await self.redis.delete(*keys)

