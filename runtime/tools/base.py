from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """
    Base interface for all tools.
    """

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool.
        """
        raise NotImplementedError

