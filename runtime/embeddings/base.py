from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EmbeddingStore(ABC):
    """
    Base interface for embedding stores.
    All embedding stores (Chroma, Pinecone, FAISS, etc.) must implement this.
    """

    @abstractmethod
    async def add_embeddings(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """
        Adds embedding vectors with metadata to the store.
        """
        pass

    @abstractmethod
    async def query_embeddings(
        self, vector: List[float], top_k: int = 10, filters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Query embeddings by similarity.
        Returns list of metadata dictionaries.
        """
        pass

    @abstractmethod
    async def delete_embeddings(self, filters: Dict[str, Any]) -> None:
        """
        Delete embeddings that match filters.
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clear the entire embedding store.
        """
        pass

