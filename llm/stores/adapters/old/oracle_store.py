import oracledb
import numpy as np

from langgraph.store.base import BaseStore
from llm.stores.store_factory import StoreFactory
 

class OracleStore(BaseStore):
    def __init__(
        self,
        dsn: str,
        user: str,
        password: str,
        table: str = "AGENT_MEMORY",
        dim: int = 1536,
    ):
        self.pool = oracledb.create_pool(
            user=user,
            password=password,
            dsn=dsn,
            min=1,
            max=10,
            increment=1,
        )
        self.table = table
        self.dim = dim

    async def put(self, key, value, *, namespace=None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table} (id, namespace, payload, embedding)
                VALUES (:1, :2, :3, :4)
                """,
                (
                    key,
                    namespace,
                    value["data"],
                    value.get("embedding"),
                ),
            )
            await conn.commit()

    async def get(self, key, *, namespace=None):
        async with self.pool.acquire() as conn:
            cur = await conn.execute(
                f"""
                SELECT payload FROM {self.table}
                WHERE id = :1 AND namespace = :2
                """,
                (key, namespace),
            )
            row = await cur.fetchone()
            return row[0] if row else None

    async def search(self, query_vector, *, namespace=None, top_k=5):
        async with self.pool.acquire() as conn:
            cur = await conn.execute(
                f"""
                SELECT payload
                FROM {self.table}
                WHERE namespace = :1
                ORDER BY embedding <-> :2
                FETCH FIRST :3 ROWS ONLY
                """,
                (namespace, query_vector, top_k),
            )
            return [row[0] for row in await cur.fetchall()]



# register dynamically
StoreFactory.register("inmemory", OracleVectorStore)



