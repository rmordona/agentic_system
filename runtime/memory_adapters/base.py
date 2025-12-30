# runtime/memory_adapters/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class MemoryAdapter(ABC):
    """
    Base interface for memory adapters (episodic or semantic).
    All adapters must implement these methods.
    """

    @abstractmethod
    async def store_memory(self, memory: BaseModel) -> str:
        """Store a memory object. Returns a unique key/id."""
        pass

    @abstractmethod
    async def fetch_memory(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch memory objects based on filters."""
        pass

    @abstractmethod
    async def clear(self, session_id: Optional[str] = None):
        """Clear memory for a session or the entire adapter."""
        pass

