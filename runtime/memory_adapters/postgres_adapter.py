# runtime/memory_adapters/postgres_adapter.py
from runtime.memory_adapters.base import MemoryAdapter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncpg
import json

class PostgresAdapter(MemoryAdapter):
    def __init__(self, dsn: str, table_name: str = "memories"):
        self.dsn = dsn
        self.table_name = table_name
        self.pool: Optional[asyncpg.Pool] = None

    async def _init_pool(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)
            # Ensure table exists
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT,
                        agent TEXT,
                        stage TEXT,
                        task TEXT,
                        memory JSONB
                    )
                    """
                )

    async def store_memory(self, memory: BaseModel) -> str:
        await self._init_pool()
        memory_dict = memory.model_dump()
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                f"""
                INSERT INTO {self.table_name} (session_id, agent, stage, task, memory)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                memory_dict.get("session_id"),
                memory_dict.get("agent"),
                memory_dict.get("stage"),
                memory_dict.get("task"),
                json.dumps(memory_dict),
            )
        return str(result["id"])

    async def fetch_memory(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = 10,
    ) -> List[Dict[str, Any]]:
        await self._init_pool()
        query = f"SELECT memory FROM {self.table_name} WHERE 1=1"
        params = []
        if session_id:
            params.append(session_id)
            query += f" AND session_id = ${len(params)}"
        if agent:
            params.append(agent)
            query += f" AND agent = ${len(params)}"
        if stage:
            params.append(stage)
            query += f" AND stage = ${len(params)}"
        if task:
            params.append(task)
            query += f" AND task = ${len(params)}"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row["memory"]) for row in rows[:top_k]]

    async def clear(self, session_id: Optional[str] = None):
        await self._init_pool()
        async with self.pool.acquire() as conn:
            if session_id:
                await conn.execute(f"DELETE FROM {self.table_name} WHERE session_id = $1", session_id)
            else:
                await conn.execute(f"DELETE FROM {self.table_name}")

