# llm/stores/base_store.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class BaseStore(ABC):
    """
    BaseStore interface for all memory stores (semantic or episodic).

    Every store supports:
      - Namespaces: group related items
      - Keys: unique identifier for items
      - Value: main content (text or object for embeddings)
      - Metadata: structured info for filtering
      - Document: full object for retrieval, logging, reflection
    """

    @abstractmethod
    async def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None,
    ):
        """
        Save an item in the store.
        """
        pass

    @abstractmethod
    async def get(
        self,
        namespace: Tuple[str, str],
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item by key.
        Returns dictionary: {"value": ..., "metadata": ..., "document": ...}
        """
        pass

    @abstractmethod
    async def query(
        self,
        namespace: Tuple[str, str],
        query: str,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic or key-based search.
        Returns a list of items: [{"key": ..., "value": ..., "metadata": ..., "document": ...}]
        """
        pass

    @abstractmethod
    async def delete(
        self,
        namespace: Tuple[str, str],
        key: str
    ):
        """
        Delete an item from the store.
        """
        pass

    @abstractmethod
    async def clear(self, namespace: Optional[Tuple[str, str]] = None):
        """
        Clear all items, optionally within a namespace.
        """
        pass
