# runtime/embedding/postgres_store.py
from typing import List, Dict, Any
import asyncpg
import psycopg2
import psycopg2.extras
import numpy as np
from runtime.embeddings.base import EmbeddingStore
from runtime.logger import AgentLogger

class PostgresEmbeddingStore(EmbeddingStore):
    """
    Persistent embedding store using PostgreSQL + pgvector.
    Supports multiple collections (tables) as defined in config.
    """
    logger = None

    def __init__(self, config: Dict[str, Any]):
        self.dsn= config.get("dsn") # Data Source Name
        self.collections = config.get("collections")
        self.pool: asyncpg.pool.Pool | None = None

        # Initialize connections and ensure tables exist
        #self.conn = psycopg2.connect(dsn)
        #self.conn.autocommit = True

        # Bind workspace logger ONCE
        if PostgresEmbeddingStore.logger is None:
            PostgresEmbeddingStore.logger = AgentLogger.get_logger(None, component="postgres_embedding")

        logger = PostgresEmbeddingStore.logger

        self.connect(dsn=self.dsn)  

        self.initialize_tables()




    async def connect(self, dsn: str):
            """
            Establish async connection pool.
            """
            if self.pool is None:
                self.pool = await asyncpg.create_pool(dsn=dsn)
                logger.info("Postgres connection pool initialized")

    async def initialize_tables(self):
            """
            Ensure tables exist for each collection.
            """
            if self.pool is None:
                raise RuntimeError("Connection pool not initialized. Call connect() first.")
            async with self.pool.acquire() as conn:
                for collection in self.collections:
                    await conn.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {collection} (
                            id SERIAL PRIMARY KEY,
                            vector DOUBLE PRECISION[],
                            metadata JSONB
                        )
                        """
                    )
                    logger.info(f"Initialized collection/table '{coll}'")
            logger.info("Postgres tables ensured")

    def add_embeddings(self, collection: str, id: str, vector: List[float], metadata: Dict[str, Any]):
        if collection not in self.collections:
            raise ValueError(f"Unknown collection '{collection}'")
        with self.conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {collection} (id, vector, metadata) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET vector = EXCLUDED.vector, metadata = EXCLUDED.metadata",
                (id, vector, psycopg2.extras.Json(metadata))
            )
        logger.debug(f"Inserted embedding {id} into collection {collection}")

    def query_embeddings(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if collection not in self.collections:
            raise ValueError(f"Unknown collection '{collection}'")
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, metadata, vector <#> %s AS distance
                FROM {collection}
                ORDER BY vector <#> %s
                LIMIT %s;
                """,
                (query_vector, query_vector, top_k)
            )
            results = cur.fetchall()
        return results

    async def delete_embeddings(self, filters: Dict[str, Any]) -> None:
        await self.connect()
        async with self.pool.acquire() as conn:
            # Example: filters could be a dict of column -> value
            where_clause = " AND ".join([f"{k} = ${i+1}" for i, k in enumerate(filters.keys())])
            values = list(filters.values())
            await conn.execute(f"DELETE FROM {self.table} WHERE {where_clause}", *values)

    async def clear(self) -> None:
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(f"TRUNCATE TABLE {self.table}")