from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncpg
import json
from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_schemas import EpisodicMemory, SemanticMemory

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

    async def store_memory(
        self,
        memory: Union[Dict, BaseModel, EpisodicMemory]
        # namespace: Optional[str] = None
    ) -> str:
        memory_dict = memory.model_dump()
        keys = dict(memory_dict.get("key_namespace"))
        await self._init_pool()
        memory_dict = memory.model_dump()
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                f"""
                INSERT INTO {self.table_name} (session_id, agent, stage, namespace, task, memory)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                keys.get("session_id"),
                keys.get("agent"),
                keys.get("stage"),
                keys.get("namespace"),
                memory_dict.get("task"),
                json.dumps(memory_dict),
            )
        return str(result["id"])

    async def fetch_memory(
        self,
        key_namespace: tuple = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:


        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["stage"]
        namespace  = keys["namespace"]

        await self._init_pool()
        query = f"SELECT memory FROM {self.table_name} WHERE 1=1"
        params = []
        if session_id:
            params.append(session_id)
            query += f" AND session_id = :session_id"
        if agent:
            params.append(agent)
            query += f" AND agent = :agent"
        if stage:
            params.append(stage)
            query += f" AND stage = :stage"
        if namespace:
            params.append(namespace)
            query += f" AND task = :namespace"

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

    async def add_embeddings(
        self,
        memory: Union[Dict, BaseModel, SemanticMemory]
    ) -> None:
        """Add embeddings to the semantic store."""
        return

    async def semantic_search(
        cls,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}

    async def nl_to_sql(
        cls,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}
