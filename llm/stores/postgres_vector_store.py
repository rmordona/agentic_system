import asyncpg

from langgraph.store.base import BaseStore
from llm.stores.store_factory import StoreFactory

class PostgresVectorStore(BaseStore):
    def __init__(
        self,
        dsn: str,
        table: str = "agent_memory",
    ):
        self.dsn = dsn
        self.table = table
        self.pool = None

    async def _pool(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn)
        return self.pool

    async def put(self, key, value, *, namespace=None):
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table} (id, namespace, payload, embedding)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE
                SET payload = EXCLUDED.payload,
                    embedding = EXCLUDED.embedding
                """,
                key,
                namespace,
                value["data"],
                value["embedding"],
            )

    async def get(self, key, *, namespace=None):
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT payload FROM {self.table}
                WHERE id = $1 AND namespace = $2
                """,
                key,
                namespace,
            )
            return row["payload"] if row else None

    async def search(self, query_vector, *, namespace=None, top_k=5):
        pool = await self._pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT payload
                FROM {self.table}
                WHERE namespace = $1
                ORDER BY embedding <-> $2
                LIMIT $3
                """,
                namespace,
                query_vector,
                top_k,
            )
            return [row["payload"] for row in rows]

# register dynamically
StoreFactory.register("postgres", PostgresVectorStore)

