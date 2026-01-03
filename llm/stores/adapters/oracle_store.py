# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/oracle_store.py
#
# Description:
#   OracleStore production-ready adapter:
#     - Semantic memory via VECTOR columns
#     - Episodic memory via JSON storage
#     - Async operations via cx_Oracle + asyncio
#     - Namespaced keys for multi-user/session isolation
#     - Supports storing metadata and documents
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# -----------------------------------------------------------------------------

from typing import Any, Dict, Tuple, List, Optional
import json
import asyncio
import cx_Oracle
import numpy as np
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.stores.adapters.base_store import BaseStore
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class OracleStore(BaseStore):
    """
    OracleStore wrapper supporting:
      1. Semantic memory (VECTOR columns)
      2. Episodic memory (JSON)
      3. Metadata/document support
      4. Namespaced keys for multi-user/session isolation
      5. Async operations
    """

    def __init__(
        self,
        dsn: str,
        embedding_client: Optional[BaseEmbeddingClient] = None,
        semantic_table: str = "SEMANTIC_MEMORIES",
        episodic_table: str = "EPISODIC_MEMORIES",
        vector_dims: int = 1536,
        namespace_prefix: str = "ags"
    ):
        self.dsn = dsn
        self.embedding_client = embedding_client
        self.vector_dims = vector_dims
        self.semantic_enabled = embedding_client is not None
        self.semantic_table = semantic_table
        self.episodic_table = episodic_table
        self.namespace_prefix = namespace_prefix
        self.conn: Optional[cx_Oracle.Connection] = None

    # --------------------------
    # Key helpers
    # --------------------------
    def _make_key(self, namespace: Tuple[str, str], key: str) -> str:
        return f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:{key}"

    # --------------------------
    # Connection
    # --------------------------
    async def connect(self):
        loop = asyncio.get_event_loop()
        self.conn = await loop.run_in_executor(None, lambda: cx_Oracle.connect(self.dsn))

    async def disconnect(self):
        if self.conn:
            await asyncio.get_event_loop().run_in_executor(None, self.conn.close)

    # --------------------------
    # Put
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
        """
        Store a memory in Oracle. Supports metadata/document.
        """
        ns_key = self._make_key(namespace, key)
        store_value = {
            "value": value,
            "metadata": metadata or {},
            "document": document or {}
        }

        cursor = self.conn.cursor()
        if semantic and self.semantic_enabled:
            vector = self.embedding_client.embed_text(value.get("text", ""))
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: cursor.execute(f"""
                MERGE INTO {self.semantic_table} t
                USING DUAL
                ON (t.key = :key)
                WHEN MATCHED THEN UPDATE SET t.text = :text, t.embedding = :embedding
                WHEN NOT MATCHED THEN INSERT (key, text, embedding) VALUES (:key, :text, :embedding)
                """, key=ns_key, text=json.dumps(store_value), embedding=vector.tolist())
            )
        else:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: cursor.execute(f"""
                MERGE INTO {self.episodic_table} t
                USING DUAL
                ON (t.key = :key)
                WHEN MATCHED THEN UPDATE SET t.value = :value
                WHEN NOT MATCHED THEN INSERT (key, value) VALUES (:key, :value)
                """, key=ns_key, value=json.dumps(store_value))
            )
        await asyncio.get_event_loop().run_in_executor(None, self.conn.commit)

    # --------------------------
    # Get
    # --------------------------
    async def get(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False
    ) -> Optional[Dict[str, Any]]:
        ns_key = self._make_key(namespace, key)
        cursor = self.conn.cursor()
        sql = f"SELECT text FROM {self.semantic_table} WHERE key = :key" if semantic and self.semantic_enabled \
            else f"SELECT value FROM {self.episodic_table} WHERE key = :key"

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cursor.execute(sql, key=ns_key).fetchone()
        )
        if result:
            return json.loads(result[0])
        return None

    # --------------------------
    # Semantic search
    # --------------------------
    async def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not self.semantic_enabled:
            raise RuntimeError("Semantic search not enabled")

        cursor = self.conn.cursor()
        query_vector = self.embedding_client.embed_text(query)
        ns_prefix = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:%"

        sql = f"SELECT key, text, embedding FROM {self.semantic_table} WHERE key LIKE :prefix"
        rows = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cursor.execute(sql, prefix=ns_prefix).fetchall()
        )

        results = []
        for key, text_json, emb_list in rows:
            emb = np.array(json.loads(emb_list))
            metadata_doc = json.loads(text_json)
            score = np.dot(emb, query_vector) / (np.linalg.norm(emb) * np.linalg.norm(query_vector))
            results.append({
                "key": key,
                "value": metadata_doc.get("value", {}),
                "metadata": metadata_doc.get("metadata", {}),
                "document": metadata_doc.get("document", {}),
                "score": float(score)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # --------------------------
    # Delete
    # --------------------------
    async def delete(self, namespace: Tuple[str, str], key: str, semantic: bool = False):
        ns_key = self._make_key(namespace, key)
        cursor = self.conn.cursor()
        table = self.semantic_table if semantic and self.semantic_enabled else self.episodic_table
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cursor.execute(f"DELETE FROM {table} WHERE key = :key", key=ns_key)
        )
        await asyncio.get_event_loop().run_in_executor(None, self.conn.commit)
