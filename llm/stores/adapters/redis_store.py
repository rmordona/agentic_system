# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/redis_store.py
#
# Description:
#   RedisStore production-ready adapter:
#     - Episodic memory: key/value storage with metadata & document
#     - Semantic memory: embedding search (RedisSearch or in-memory cosine)
#     - Namespaced keys for multi-user isolation
#     - Async operations
#     - Supports both persistent Redis or volatile/in-memory Redis
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# -----------------------------------------------------------------------------

from typing import Any, Dict, Tuple, List, Optional
import json
import numpy as np
import aioredis
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.stores.adapters.base_store import BaseStore
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class RedisStore(BaseStore):
    """
    RedisStore wrapper supporting:
      1. Episodic memory (key/value) with metadata and document
      2. Optional semantic search using vector embeddings
      3. Namespaced keys for multi-user/session isolation
    """

    def __init__(
        self,
        redis_url: str,
        embedding_client: Optional[BaseEmbeddingClient] = None,
        semantic_index_name: str = "semantic_idx",
        namespace_prefix: str = "ags"
    ):
        self.redis_url = redis_url
        self.embedding_client = embedding_client
        self.semantic_enabled = embedding_client is not None
        self.semantic_index_name = semantic_index_name
        self.namespace_prefix = namespace_prefix
        self.redis: Optional[aioredis.Redis] = None

    # --------------------------
    # Connection
    # --------------------------
    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url)

    async def disconnect(self):
        if self.redis:
            await self.redis.close()

    # --------------------------
    # Namespaced key helper
    # --------------------------
    def _make_key(self, namespace: Tuple[str, str], key: str) -> str:
        user_ns, context = namespace
        return f"{self.namespace_prefix}:{user_ns}:{context}:{key}"

    # --------------------------
    # Key/Value (Episodic) with metadata/document
    # --------------------------
    async def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None,
        semantic: bool = False
    ):
        ns_key = self._make_key(namespace, key)
        if semantic and self.semantic_enabled:
            # Semantic storage with embedding
            vector = self.embedding_client.embed_text(value.get("text", ""))
            await self.redis.hset(ns_key, mapping={
                "text": json.dumps(value),
                "embedding": json.dumps(vector.tolist()),
                "metadata": json.dumps(metadata or {}),
                "document": json.dumps(document or {})
            })
        else:
            # Episodic storage with metadata/document
            await self.redis.hset(ns_key, mapping={
                "value": json.dumps(value),
                "metadata": json.dumps(metadata or {}),
                "document": json.dumps(document or {})
            })

    async def get(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False
    ) -> Optional[Dict[str, Any]]:
        ns_key = self._make_key(namespace, key)
        data = await self.redis.hgetall(ns_key)
        if not data:
            return None

        if semantic and self.semantic_enabled:
            return {
                "value": json.loads(data[b"text"].decode()),
                "metadata": json.loads(data.get(b"metadata", b"{}").decode()),
                "document": json.loads(data.get(b"document", b"{}").decode())
            }
        else:
            return {
                "value": json.loads(data.get(b"value', b"{}").decode()),
                "metadata": json.loads(data.get(b"metadata", b"{}").decode()),
                "document": json.loads(data.get(b"document", b"{}").decode())
            }

    # --------------------------
    # Semantic Search (in-memory approximation)
    # --------------------------
    async def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not self.semantic_enabled:
            raise RuntimeError("Semantic search not enabled")

        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        query_vector = self.embedding_client.embed_text(query)
        results = []

        for k in keys:
            data = await self.redis.hgetall(k)
            if b"embedding" not in data:
                continue
            emb = np.array(json.loads(data[b"embedding"].decode()))
            score = float(np.dot(emb, query_vector) / (np.linalg.norm(emb) * np.linalg.norm(query_vector)))
            results.append({
                "key": k.decode(),
                "value": json.loads(data[b"text"].decode()),
                "metadata": json.loads(data.get(b"metadata", b"{}").decode()),
                "document": json.loads(data.get(b"document", b"{}").decode()),
                "score": score
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # --------------------------
    # Utilities
    # --------------------------
    async def delete(self, namespace: Tuple[str, str], key: str):
        ns_key = self._make_key(namespace, key)
        await self.redis.delete(ns_key)

    async def clear_namespace(self, namespace: Tuple[str, str]):
        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        if keys:
            await self.redis.delete(*keys)

    async def count_namespace(self, namespace: Tuple[str, str]) -> int:
        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        return len(keys)
