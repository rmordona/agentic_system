# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/postgres_store.py
#
# Description:
#   Production-ready PostgresStore supporting:
#     - Semantic memory via pgvector (HNSW/cosine similarity)
#     - Episodic memory via raw JSON storage
#     - Metadata and document support for filtering and logging
#     - Async operations for modern Python applications
#     - Namespaced keys for multi-user isolation
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from typing import Any, Dict, Optional, Tuple, List
import asyncio
import json
from databases import Database
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.stores.adapters.base_store import BaseStore
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class PostgresStore(BaseStore):
    """
    Production-ready PostgresStore.
    - Semantic memory: pgvector
    - Episodic memory: JSON/text
    - Supports metadata and document storage
    - Namespaced keys
    """

    def __init__(
        self,
        database_url: str,
        embedding_client: Optional[BaseEmbeddingClient] = None,
        vector_dims: Optional[int] = None,
        semantic_table: str = "semantic_memories",
        episodic_table: str = "episodic_memories",
        namespace_prefix: str = "ags"
    ):
        self.database_url = database_url
        self.db = Database(database_url)
        self.embedding_client = embedding_client
        self.vector_dims = vector_dims
        self.semantic_table = semantic_table
        self.episodic_table = episodic_table
        self.semantic_enabled = embedding_client is not None and vector_dims is not None
        self.namespace_prefix = namespace_prefix

    # --------------------------
    # Namespaced key helper
    # --------------------------
    def _make_key(self, namespace: Tuple[str, str], key: str) -> str:
        user_ns, context = namespace
        return f"{self.namespace_prefix}:{user_ns}:{context}:{key}"

    # --------------------------
    # Connection
    # --------------------------
    async def connect(self):
        await self.db.connect()
        await self._create_tables()

    async def disconnect(self):
        await self.db.disconnect()

    async def _create_tables(self):
        """
        Create semantic and episodic tables if not exists.
        Semantic table requires pgvector extension.
        """
        if self.semantic_enabled:
            await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.semantic_table} (
                key TEXT PRIMARY KEY,
                namespace TEXT,
                text JSONB,
                embedding VECTOR({self.vector_dims})
            );
            """)

        await self.db.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.episodic_table} (
            key TEXT PRIMARY KEY,
            namespace TEXT,
            value JSONB,
            metadata JSONB,
            document JSONB
        );
        """)

    # --------------------------
    # Key/Value Storage with metadata/document
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
            vector = self.embedding_client.embed_text(value.get("text", ""))  # assumes 'text' field
            await self.db.execute(
                f"""
                INSERT INTO {self.semantic_table} (key, namespace, text, embedding)
                VALUES (:key, :namespace, :text, :embedding)
                ON CONFLICT (key) DO UPDATE
                  SET text = :text, embedding = :embedding;
                """,
                values={
                    "key": ns_key,
                    "namespace": f"{namespace[0]}:{namespace[1]}",
                    "text": json.dumps(value),
                    "embedding": vector.tolist()
                }
            )
        else:
            await self.db.execute(
                f"""
                INSERT INTO {self.episodic_table} (key, namespace, value, metadata, document)
                VALUES (:key, :namespace, :value, :metadata, :document)
                ON CONFLICT (key) DO UPDATE
                  SET value = :value, metadata = :metadata, document = :document;
                """,
                values={
                    "key": ns_key,
                    "namespace": f"{namespace[0]}:{namespace[1]}",
                    "value": json.dumps(value),
                    "metadata": json.dumps(metadata or {}),
                    "document": json.dumps(document or {})
                }
            )

    async def get(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False
    ) -> Optional[Dict[str, Any]]:
        ns_key = self._make_key(namespace, key)
        if semantic and self.semantic_enabled:
            row = await self.db.fetch_one(
                f"SELECT text FROM {self.semantic_table} WHERE key = :key",
                values={"key": ns_key}
            )
        else:
            row = await self.db.fetch_one(
                f"SELECT value, metadata, document FROM {self.episodic_table} WHERE key = :key",
                values={"key": ns_key}
            )
        if row:
            if semantic and self.semantic_enabled:
                return json.loads(row[0])
            else:
                return {
                    "value": json.loads(row["value"]),
                    "metadata": json.loads(row["metadata"]),
                    "document": json.loads(row["document"])
                }
        return None

    # --------------------------
    # Semantic Search
    # --------------------------
    async def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not self.semantic_enabled:
            raise RuntimeError("Semantic search not enabled.")

        query_vector = self.embedding_client.embed_text(query)
        ns_value = f"{namespace[0]}:{namespace[1]}"

        rows = await self.db.fetch_all(
            f"""
            SELECT key, text, embedding <#> :query_vector AS score
            FROM {self.semantic_table}
            WHERE namespace = :namespace
            ORDER BY embedding <#> :query_vector
            LIMIT :limit
            """,
            values={
                "query_vector": query_vector.tolist(),
                "namespace": ns_value,
                "limit": limit
            }
        )

        return [{"key": r["key"], "value": json.loads(r["text"]), "score": r["score"]} for r in rows]

    # --------------------------
    # Utilities
    # --------------------------
    async def delete(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False
    ):
        ns_key = self._make_key(namespace, key)
        table = self.semantic_table if semantic else self.episodic_table
        await self.db.execute(f"DELETE FROM {table} WHERE key = :key", values={"key": ns_key})

    async def clear_namespace(
        self,
        namespace: Tuple[str, str],
        semantic: bool = False
    ):
        ns_value = f"{namespace[0]}:{namespace[1]}"
        table = self.semantic_table if semantic else self.episodic_table
        await self.db.execute(f"DELETE FROM {table} WHERE namespace = :namespace", values={"namespace": ns_value})

    async def count_namespace(
        self,
        namespace: Tuple[str, str],
        semantic: bool = False
    ) -> int:
        ns_value = f"{namespace[0]}:{namespace[1]}"
        table = self.semantic_table if semantic else self.episodic_table
        row = await self.db.fetch_one(
            f"SELECT COUNT(*) FROM {table} WHERE namespace = :namespace",
            values={"namespace": ns_value}
        )
        return row[0] if row else 0
