# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/chromadb_store.py
#
# Description:
#   ChromaDBStore production-ready adapter:
#     - Persistent or in-memory vector search
#     - Semantic memory using embeddings
#     - Episodic memory with metadata/document
#     - Async operations
#     - Namespaced collections for multi-user isolation
#     - Supports connecting to a Chroma endpoint via URL
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# -----------------------------------------------------------------------------

from typing import Any, Dict, Tuple, List, Optional
import chromadb
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.stores.adapters.base_store import BaseStore
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class ChromaDBStore(BaseStore):
    """
    ChromaDBStore wrapper supporting:
      1. Semantic memory with embeddings
      2. Episodic memory with metadata and documents
      3. Namespaced collections for multi-user/session isolation
      4. Async-ready API
      5. Optional endpoint URL for remote Chroma server
    """

    def __init__(
        self,
        embedding_client: BaseEmbeddingClient,
        persist_directory: Optional[str] = None,
        chroma_url: Optional[str] = None,
        namespace_prefix: str = "ags"
    ):
        self.embedding_client = embedding_client
        self.namespace_prefix = namespace_prefix
        self.persist_directory = persist_directory
        self.chroma_url = chroma_url

        if chroma_url:
            # Connect to remote Chroma server
            self.client = chromadb.Client(chroma_url=chroma_url)
            logger.info(f"ChromaDBStore connected to remote endpoint: {chroma_url}")
        else:
            # Local persistent or in-memory
            self.client = chromadb.Client(persist_directory=persist_directory)
            if persist_directory:
                logger.info(f"ChromaDBStore using local persistence at: {persist_directory}")
            else:
                logger.info("ChromaDBStore using in-memory local client")

        self.collections: Dict[str, Any] = {}

    # --------------------------
    # Collection helpers
    # --------------------------
    def _get_collection_name(self, namespace: Tuple[str, str]) -> str:
        return f"{self.namespace_prefix}_{namespace[0]}_{namespace[1]}"

    def _get_or_create_collection(self, namespace: Tuple[str, str]):
        name = self._get_collection_name(namespace)
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_client.embed_text
            )
        return self.collections[name]

    # --------------------------
    # Key/Value Put
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
        collection = self._get_or_create_collection(namespace)
        store_value = {
            "value": value,
            "metadata": metadata or {},
            "document": document or {}
        }

        if semantic:
            embedding = self.embedding_client.embed_text(value.get("text", ""))
            collection.add(
                ids=[key],
                metadatas=[store_value],
                embeddings=[embedding]
            )
        else:
            # Episodic memory: dummy vector for Chroma
            collection.add(
                ids=[key],
                metadatas=[store_value],
                embeddings=[[0]*1536]
            )

    # --------------------------
    # Key/Value Get
    # --------------------------
    async def get(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False
    ) -> Optional[Dict[str, Any]]:
        collection = self._get_or_create_collection(namespace)
        results = collection.get(ids=[key])
        if results["ids"]:
            return results["metadatas"][0]
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
        collection = self._get_or_create_collection(namespace)
        embedding = self.embedding_client.embed_text(query)
        results = collection.query(query_embeddings=[embedding], n_results=limit)

        return [
            {
                "key": r_id,
                "value": metadata.get("value", {}),
                "metadata": metadata.get("metadata", {}),
                "document": metadata.get("document", {}),
                "score": float(score)
            }
            for r_id, metadata, score in zip(
                results["ids"][0], results["metadatas"][0], results["distances"][0]
            )
        ]

    # --------------------------
    # Delete
    # --------------------------
    async def delete(self, namespace: Tuple[str, str], key: str):
        collection = self._get_or_create_collection(namespace)
        collection.delete(ids=[key])

    # --------------------------
    # Clear entire namespace
    # --------------------------
    async def clear_namespace(self, namespace: Tuple[str, str]):
        collection = self._get_or_create_collection(namespace)
        ids = collection.get()["ids"]
        if ids:
            collection.delete(ids=ids)

    # --------------------------
    # Count entries
    # --------------------------
    async def count_namespace(self, namespace: Tuple[str, str]) -> int:
        collection = self._get_or_create_collection(namespace)
        ids = collection.get()["ids"]
        return len(ids)
