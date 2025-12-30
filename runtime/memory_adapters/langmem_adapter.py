from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from langmem import create_memory_manager, create_memory_searcher
from runtime.memory_adapters.base import MemoryAdapter
from llm.local_llm import LocalLLM, LocalLLMChatModel

class LangMemSemanticAdapter(MemoryAdapter):
    """
    Session-scoped semantic memory adapter backed by LangMem.
    """

    def __init__(self, chat_model, schemas: List[type[BaseModel]]):
        self.manager = create_memory_manager(
            chat_model,
            schemas=schemas
        )

        self.searcher = create_memory_searcher( chat_model)

    async def store_memory(self, memory: BaseModel) -> str:
        """
        Stores a memory object in Redis. Returns the generated key.
        """
        key = str(uuid4())
        langmem_key = self._key(memory.session_id, key)

        await self.manager.add(memory.model_dump_json() )
        return langmem_key

    async def fetch_memory(
        self,
        session_id: Optional[str] = None,
        task: Optional[str] = None,
        stage: Optional[str | list[str]] = None,
        agent: Optional[str | list[str]] = None,
        filters: Optional[Dict[str, Any]] = None, 
        top_k: Optional[int] = None,
       #limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Fetch semantic memories via metadata filtering.
        """
        filters = {}

        if session_id:
            filters["session_id"] = session_id
        if task:
            filters["task"] = task
        if agent:
            filters["agent"] = agent
        if stage:
            filters["stage"] = stage

        return await self.searcher.search(
            query="",
            filters=filters,
            limit=limit,
        )

    async def semantic_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        filters = {}
        if session_id:
            filters["session_id"] = session_id

        return await self.searcher.search(
            query=query,
            filters=filters,
            limit=limit,
        )

    async def clear(self):
        """Delete all keys in this namespace."""
        return
