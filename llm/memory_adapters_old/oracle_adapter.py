# runtime/memory_adapters/oracle_adapter.py
import json
import asyncio
import oracledb
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from llm.memory_adapters.base import MemoryAdapter
from llm.memory_schemas import EpisodicMemory, SemanticMemory

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
        memory: Union[Dict, BaseModel, EpisodicMemory]
    ) -> str:
        memory_dict = memory.model_dump()
        keys = dict(memory_dict.get("key_namespace"))
        await self._init_pool()
        loop = asyncio.get_event_loop()
        async with asyncio.Lock():
            def _insert():
                with self.pool.acquire() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"INSERT INTO {self.table_name} (session_id, agent, stage, namespace, task, memory) VALUES (:1, :2, :3, :4, :5, :6) RETURNING rowid INTO :6",
                            (keys.get("session_id"), 
                             keys.get("agent"),
                             keys.get("stage"), 
                             keys.get("namespace"),
                             memory_dict.get("task"),
                             json.dumps(memory_dict), None)
                        )
                        return cur.fetchone()[0]
            key = await loop.run_in_executor(None, _insert)
        return key

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
                        if namespace:
                            query += " AND namespace = :namespace"
                            params["namespace"] = namespace
                        cur.execute(query, params)
                        return [json.loads(r[0]) for r in cur.fetchall()]
            return (await loop.run_in_executor(None, _query))[:top_k]

    
    async def add_embeddings(
        self,
        memory: Union[Dict, BaseModel, SemanticMemory]
    ) -> None:
        """Add embeddings to the semantic store."""
        return

    async def semantic_search(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}

    async def query(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}


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