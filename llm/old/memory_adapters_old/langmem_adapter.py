from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from langmem import create_memory_manager 
from langchain_core.runnables import Runnable
from llm.memory_adapters.base import MemoryAdapter
from llm.memory_schemas import EpisodicMemory, SemanticMemory

#from llm.llm_manager import LLMManager

class LangMemSemanticAdapter(MemoryAdapter):
    """
    Session-scoped semantic memory adapter backed by LangMem.
    """

    def __init__(self, chat_model, schemas: List[type[BaseModel]]):
        self.manager = create_memory_manager(
            chat_model,
            schemas=schemas
        )


    def _key(self, session_id: str, namespace: str, uid: str):
        return f"{session_id}:{self.namespace}:{uid}"

    async def store_memory(
        self,
        memory: Union[Dict, BaseModel, EpisodicMemory]
        # namespace: Optional[str] = None
    ) -> str:
        """
        Stores a memory object in Redis. Returns the generated key.
        """
        key = str(uuid4())
        langmem_key = self._key(memory.session_id, memory.namespace, key)

        await self.manager.add(memory.model_dump_json() )
        return langmem_key


    async def fetch_memory(
        self,
        key_namespace: tuple = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch semantic memories via metadata filtering.
        """
        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["stage"]
        namespace  = keys["namespace"]

        '''
        filters = {}

        if session_id:
            filter["session_id"] = session_id
        if task:
            filter["task"] = task
        if agent:
            filter["agent"] = agent
        if stage:
            filter["stage"] = stage
        '''

        # Call the RunnableSequence instead of .search()
        # It will return a list of results
        #results = await self.searcher.arun(query, k=top_k)
        # results = await Runnable(self.searcher).arun(query)
        #results = await self.searcher.search(query, k=top_k)
        
        # Or if synchronous context:
        # results = self.searcher.run(query, k=top_k)

        result = None
        return results


    async def add_embeddings(
        self,
        memory: Union[Dict, BaseModel, SemanticMemory]
    ) -> None:
        """Add embeddings to the semantic store."""
        return

    async def semantic_search(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        '''
        return await self.searcher.search(
            query=query,
            filters=filters,
            limit=limit,
        )
        '''
        return None

    async def query(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        '''
        return await self.searcher.search(
            query=query,
            filters=filters,
            limit=limit,
        )
        '''
        return None

    async def clear(self):
        """Delete all keys in this namespace."""
        return