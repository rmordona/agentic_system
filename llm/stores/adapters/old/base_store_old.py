from typing import Any, Dict, List, Optional
from langgraph.store.base import BaseStore


class SemanticStore(BaseStore):
    """
    SemanticStore
    -------------
    Vector-based store for long-term knowledge.

    Responsibilities:
    - Store embeddings + metadata
    - Perform similarity search
    - Support decay / summarization hooks

    This class is storage-agnostic and may be backed by:
    - Vector DB (Chroma, Pinecone, Weaviate)
    - Hybrid DB (Postgres + pgvector)
    """

    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        raise NotImplementedError("SemanticStore.save must be implemented")

    async def similarity_search(
        self,
        vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("SemanticStore.similarity_search must be implemented")

    async def update_metadata(
        self,
        key: str,
        metadata: Dict[str, Any],
    ) -> None:
        raise NotImplementedError("SemanticStore.update_metadata must be implemented")

    async def stats(self, key: str) -> Dict[str, Any]:
        raise NotImplementedError("SemanticStore.stats must be implemented")

    async def summarize(self, key: str) -> None:
        """
        Optional: collapse multiple entries into a summary vector.
        """
        raise NotImplementedError("SemanticStore.summarize must be implemented")

    async def count(self) -> int:
        raise NotImplementedError("SemanticStore.count must be implemented")

    async def clear(self) -> None:
        raise NotImplementedError("SemanticStore.clear must be implemented")


class EpisodicStore(BaseStore):
    """
    EpisodicStore
    -------------
    Event-based memory store for agent experiences.

    Responsibilities:
    - Store raw events
    - Preserve temporal order
    - Enable replay, inspection, and reflection

    Typically backed by:
    - Key-value store
    - Document DB
    - Relational DB
    """

    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        raise NotImplementedError("EpisodicStore.save must be implemented")

    async def query(
        self,
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("EpisodicStore.query must be implemented")

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("EpisodicStore.get must be implemented")

    async def count(self) -> int:
        raise NotImplementedError("EpisodicStore.count must be implemented")

    async def clear(self) -> None:
        raise NotImplementedError("EpisodicStore.clear must be implemented")



