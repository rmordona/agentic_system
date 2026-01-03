# -----------------------------------------------------------------------------
# File: llm/stores/postgres_episodic_store.py
# -----------------------------------------------------------------------------

import asyncpg
from typing import Any, Dict, List, Optional

from llm.stores.base import EpisodicStore


class PostgresEpisodicStore(EpisodicStore):
    """
    Persistent episodic store using Postgres (no pgvector).
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.dsn)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    key TEXT PRIMARY KEY,
                    value JSONB,
                    created_at TIMESTAMP DEFAULT now()
                );
                """
            )

    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO episodic_memory(key, value)
                VALUES($1,$2)
                ON CONFLICT (key)
                DO UPDATE SET value=$2
                """,
                key,
                value,
            )

    async def fetch(
        self,
        key: Optional[str] = None,
        limit: int = 10,
    ):
        async with self.pool.acquire() as conn:
            if key:
                row = await conn.fetchrow(
                    "SELECT value FROM episodic_memory WHERE key=$1", key
                )
                return [dict(row)] if row else []
            rows = await conn.fetch(
                "SELECT value FROM episodic_memory ORDER BY created_at DESC LIMIT $1",
                limit,
            )
            return [dict(r) for r in rows]

    async def delete(self, key: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM episodic_memory WHERE key=$1", key
            )

    async def clear(self):
        async with self.pool.acquire() as conn:
            await conn.execute("TRUNCATE episodic_memory")

