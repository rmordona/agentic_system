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
        reward: Optional[float] = None
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
    async def search(
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
    async def delete(self, namespace: Tuple[str, str], key: str):
        ns_key = self._make_key(namespace, key)
        await self.redis.delete(ns_key)

    @abstractmethod
    async def clear_namespace(self, namespace: Tuple[str, str]):
        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        if keys:
            await self.redis.delete(*keys)

    @abstractmethod
    async def count_namespace(self, namespace: Tuple[str, str]) -> int:
        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        return len(keys)