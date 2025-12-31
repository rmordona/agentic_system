# runtime/memory_adapters/oracle_adapter.py
from runtime.memory_adapters.base import MemoryAdapter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import oracledb
import json
import asyncio

class OracleAdapter(MemoryAdapter):
    def __init__(self, dsn: str, table_name: str = "memories"):
        self.dsn = dsn
        self.table_name = table_name
        self.pool: Optional[oracledb.SessionPool] = None

    async def _init_pool(self):
        if self.pool is None:
            loop = asyncio.get_event_loop()
            self.pool = await loop.run_in_executor(None, lambda: oracledb.create_pool(user="user", password="pass", dsn=self.dsn, min=1, max=5))
            # Table creation can be handled outside in production

    async def store_memory(
        self,
        memory: BaseModel,
        namespace: Optional[str] = None
    ) -> str:
        await self._init_pool()
        memory_dict = memory.model_dump()
        loop = asyncio.get_event_loop()
        async with asyncio.Lock():
            def _insert():
                with self.pool.acquire() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"INSERT INTO {self.table_name} (session_id, agent, stage, task, memory) VALUES (:1, :2, :3, :4, :5) RETURNING rowid INTO :6",
                            (memory_dict.get("session_id"), memory_dict.get("agent"),
                             memory_dict.get("stage"), memory_dict.get("task"),
                             json.dumps(memory_dict), None)
                        )
                        return cur.fetchone()[0]
            key = await loop.run_in_executor(None, _insert)
        return key

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
        await self._init_pool()
        loop = asyncio.get_event_loop()
        async with asyncio.Lock():
            def _query():
                with self.pool.acquire() as conn:
                    with conn.cursor() as cur:
                        query = f"SELECT memory FROM {self.table_name} WHERE 1=1"
                        params = {}
                        if session_id:
                            query += " AND session_id = :session_id"
                            params["session_id"] = session_id
                        if agent:
                            query += " AND agent = :agent"
                            params["agent"] = agent
                        if stage:
                            query += " AND stage = :stage"
                            params["stage"] = stage
                        if task:
                            query += " AND task = :task"
                            params["task"] = task
                        cur.execute(query, params)
                        return [json.loads(r[0]) for r in cur.fetchall()]
            return (await loop.run_in_executor(None, _query))[:top_k]

    async def clear(self, session_id=None):
        await self._init_pool()
        loop = asyncio.get_event_loop()
        async with asyncio.Lock():
            def _clear():
                with self.pool.acquire() as conn:
                    with conn.cursor() as cur:
                        if session_id:
                            cur.execute(f"DELETE FROM {self.table_name} WHERE session_id = :1", [session_id])
                        else:
                            cur.execute(f"DELETE FROM {self.table_name}")
            await loop.run_in_executor(None, _clear)

