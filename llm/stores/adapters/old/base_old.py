# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/base.py
#
# Description:
#   Defines the abstract base interfaces for SemanticStore and EpisodicStore.
#   These interfaces formalize the contract for memory persistence layers used
#   by agents, independent of backend (InMemory, Redis, Postgres, etc.).
#
#   SemanticStore:
#     - Stores embedded representations of knowledge
#     - Supports vector similarity search (cosine / ANN)
#
#   EpisodicStore:
#     - Stores chronological or event-based memory
#     - No embeddings or vector search
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# =============================================================================
# Semantic Memory Interface
# =============================================================================

class SemanticStore(ABC):
    """
    Abstract interface for semantic memory storage.

    Semantic memory stores meaning-based representations of information.
    Implementations MUST support vector similarity search using embeddings.

    Typical backends:
      - In-memory + HNSW
      - Redis + RediSearch
      - Postgres + pgvector
    """

    @abstractmethod
    async def save(
        self,
        key: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Persist a semantic memory entry.

        Args:
            key: Unique identifier for the memory item.
            text: Original text or content.
            embedding: Vector embedding of the text.
            metadata: Optional structured metadata.
            ttl_seconds: Optional expiration in seconds.
        """
        raise NotImplementedError

    @abstractmethod
    async def similarity_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most similar semantic memories.

        Args:
            embedding: Query embedding.
            top_k: Number of results to return.
            metadata_filter: Optional filter constraints.

        Returns:
            A list of result dictionaries, typically containing:
              - key
              - text
              - score
              - metadata
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Remove a semantic memory entry.

        Args:
            key: Identifier of the memory to delete.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """
        Remove all semantic memory entries.
        """
        raise NotImplementedError


# =============================================================================
# Episodic Memory Interface
# =============================================================================

class EpisodicStore(ABC):
    """
    Abstract interface for episodic memory storage.

    Episodic memory stores time-based, event-based, or reflective data.
    Implementations MUST NOT perform embedding or vector similarity search.

    Typical backends:
      - In-memory store
      - Redis (hashes / TTL)
      - Postgres (relational tables)
    """

    @abstractmethod
    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Persist an episodic memory entry.

        Args:
            key: Unique identifier for the episode.
            value: Arbitrary structured data.
            ttl_seconds: Optional expiration in seconds.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodic memories.

        Args:
            key: Optional specific key to fetch.
            limit: Maximum number of entries to return.

        Returns:
            A list of episodic memory entries.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Remove an episodic memory entry.

        Args:
            key: Identifier of the episode to delete.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """
        Remove all episodic memory entries.
        """
        raise NotImplementedError

