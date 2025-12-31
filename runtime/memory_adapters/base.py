# runtime/memory_adapters/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel


class MemoryAdapter(ABC):
    """
    Base interface for memory adapters.

    This is a pure abstract contract.

    All methods are classmethods and must be implemented
    by concrete adapter subclasses.

    Adapters may support:
      - Episodic (persistent / CRUD) memory
      - Semantic (embedding-based) memory
      - Or both
    """

    # ============================================================
    # Episodic Memory (Persistent / CRUD)
    # ============================================================

    @classmethod
    @abstractmethod
    async def store_memory(
        cls,
        memory: BaseModel,
        namespace: Optional[str] = None,
    ) -> str:
        """Store a memory object and return a unique ID."""
        pass

    @classmethod
    @abstractmethod
    async def fetch_memory(
        cls,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        *,
        top_k: Optional[int] = 5,
        limit: Optional[int] = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetch episodic memory objects based on filters and/or query.
        """
        pass

    # ============================================================
    # Semantic Memory (Embeddings / Vector Search)
    # ============================================================

    @classmethod
    @abstractmethod
    async def add_embeddings(
        cls,
        *,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Optional[Sequence[str]] = None,
        metadatas: Optional[Sequence[Dict[str, Any]]] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Add embeddings to the semantic store."""
        pass


    @classmethod
    @abstractmethod
    async def query(
        cls,
        *,
        query_embedding: Sequence[float],
        namespace: Optional[str] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        pass

    # ============================================================
    # Lifecycle
    # ============================================================

    @classmethod
    @abstractmethod
    async def clear(
        cls,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Clear memory for a namespace, session, or entirely."""
        pass
