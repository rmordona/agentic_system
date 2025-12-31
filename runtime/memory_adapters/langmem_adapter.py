from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from langmem import create_memory_manager, create_memory_searcher
from langchain_core.runnables import Runnable
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

    async def store_memory(
        self,
        memory: BaseModel,
        namespace: Optional[str] = None
    ) -> str:
        """
        Stores a memory object in Redis. Returns the generated key.
        """
        key = str(uuid4())
        langmem_key = self._key(memory.session_id, key)

        await self.manager.add(memory.model_dump_json() )
        return langmem_key

    async def fetch_memory(
        self,
        namespace: Optional[str] = None,
        offset: Optional[str]  = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        *,
        top_k: Optional[int] = 5,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch semantic memories via metadata filtering.
        """
        filters = {}

        if session_id:
            filter["session_id"] = session_id
        if task:
            filter["task"] = task
        if agent:
            filter["agent"] = agent
        if stage:
            filter["stage"] = stage

        # Call the RunnableSequence instead of .search()
        # It will return a list of results
        #results = await self.searcher.arun(query, k=top_k)
        # results = await Runnable(self.searcher).arun(query)
        results = await self.searcher.search(query, k=top_k)
        
        # Or if synchronous context:
        # results = self.searcher.run(query, k=top_k)


        return results

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
