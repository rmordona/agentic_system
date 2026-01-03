# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/inmemory_store.py
#
# Description:
#   Production-ready InMemoryStore wrapper supporting:
#     - Key/value storage for episodic memory, user preferences
#     - Semantic search via vector embeddings + HNSW indexing
#     - Metadata and document support for advanced filtering and retrieval
#     - Namespaced keys for multi-user or multi-context usage
#     - Async-ready API for integration with async workflows
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from typing import Any, Dict, Optional, Tuple, List
from langgraph.store.memory import InMemoryStore as LGInMemoryStore
import numpy as np
from llm.embeddings.base_client import BaseEmbeddingClient
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class InMemoryStore:
    """
    Production-ready in-memory store supporting:
      1. Key/value storage for raw episodic memory
      2. Metadata and document storage
      3. Optional semantic search using vector embeddings
    """

    def __init__(
        self,
        index: Optional[Dict[str, Any]] = None,
        embedding_client: Optional[BaseEmbeddingClient] = None
    ):
        """
        Args:
            index: dict with "embed", "dims", "fields" keys to initialize HNSW index
            embedding_client: instance of BaseEmbeddingClient to vectorize text for semantic search
        """
        self.store = LGInMemoryStore()
        self.embedding_client = embedding_client
        self.semantic_index_enabled = False

        if index and embedding_client:
            # Enable semantic search mode
            self.store = LGInMemoryStore(index=index)
            self.semantic_index_enabled = True

    # --------------------------
    # Key/Value + Metadata + Document Operations
    # --------------------------
    def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None
    ):
        """
        Store a value under a namespaced key, with optional metadata and full document.

        Args:
            namespace: tuple like ("user_123", "settings") or ("user_123", "memories")
            key: unique key under namespace
            value: main value (text or object)
            metadata: optional structured data for filtering
            document: optional full object for retrieval, logging, or reflection
        """
        item = {
            "value": value,
            "metadata": metadata or {},
            "document": document or {}
        }

        if self.semantic_index_enabled and self.embedding_client:
            # Compute embedding vector for semantic search
            item["vector"] = self.embedding_client.embed_text(value)

        self.store.put(namespace, key, item)

    def get(self, namespace: Tuple[str, str], key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a stored value, including metadata and document
        """
        return self.store.get(namespace, key)

    def delete(self, namespace: Tuple[str, str], key: str):
        """
        Delete a stored value by key
        """
        self.store.delete(namespace, key)

    # --------------------------
    # Semantic Search
    # --------------------------
    def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on stored objects.

        Args:
            namespace: tuple defining the namespace
            query: natural language query string
            limit: maximum number of results
            metadata_filter: optional dict to filter items by metadata

        Returns:
            List of items with 'key', 'value', 'metadata', 'document', 'score' (cosine similarity)
        """
        if not self.semantic_index_enabled or not self.embedding_client:
            raise RuntimeError("Semantic search not enabled. Provide embeddings and initialize index.")

        # Embed query
        query_vector = self.embedding_client.embed_text(query)

        # Perform similarity search using HNSW / cosine similarity
        results = self.store.search(namespace, query=query_vector, limit=limit)

        # Optional metadata filtering
        if metadata_filter:
            def matches_metadata(item):
                return all(item["metadata"].get(k) == v for k, v in metadata_filter.items())
            results = [r for r in results if matches_metadata(r)]

        return results

    # --------------------------
    # Utility Methods
    # --------------------------
    def clear_namespace(self, namespace: Tuple[str, str]):
        """
        Clears all keys under a namespace
        """
        keys = list(self.store.keys(namespace))
        for key in keys:
            self.store.delete(namespace, key)

    def count_namespace(self, namespace: Tuple[str, str]) -> int:
        """
        Count the number of entries under a namespace
        """
        return len(list(self.store.keys(namespace)))
