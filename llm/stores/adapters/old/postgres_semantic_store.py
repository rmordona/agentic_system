# -----------------------------------------------------------------------------
# File: llm/stores/postgres_semantic_store.py
# -----------------------------------------------------------------------------

import asyncpg
from typing import Any, Dict, List, Optional

from llm.stores.base import SemanticStore


class PostgresSemanticStore(SemanticStore):
    """
    Persistent semantic store using Postgres + pgvector.
    """

    def __init__(self, dsn: str, dim: int = 768):
        self.dsn = dsn
        self.dim = dim
        self.pool: asyncpg.Pool | None = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.dsn)
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    key TEXT PRIMARY KEY,
                    text TEXT,
                    embedding VECTOR({self.dim}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT now()
                );
                """
            )

    async def save(
        self,
        key: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO semantic_memory(key, text, embedding, metadata)
                VALUES($1,$2,$3,$4)
                ON CONFLICT (key)
                DO UPDATE SET text=$2, embedding=$3, metadata=$4
                """,
                key,
                text,
                embedding,
                metadata or {},
            )

    async def similarity_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT key, text, metadata,
                       1 - (embedding <=> $1) AS score
                FROM semantic_memory
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                embedding,
                top_k,
            )
            return [dict(r) for r in rows]

    async def delete(self, key: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM semantic_memory WHERE key=$1", key
            )

    async def clear(self):
        async with self.pool.acquire() as conn:
            await conn.execute("TRUNCATE semantic_memory")

