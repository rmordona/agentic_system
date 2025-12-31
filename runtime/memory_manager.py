import asyncio
from collections import defaultdict
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_schemas import EpisodicMemory, SemanticMemory
from runtime.logger import AgentLogger


class MemoryManager:
    """
    Fully pluggable memory manager:
    - episodic: MemoryAdapter
    - semantic: MemoryAdapter
    """

    def __init__(self, episodic: Optional[MemoryAdapter] = None, semantic: Optional[MemoryAdapter] = None):
        self.lock = asyncio.Lock()
        self.episodic_adapter = episodic
        self.semantic_adapter = semantic
        self.in_memory_episodic: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self.in_memory_semantic: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(None, component="system")

    # ------------------------------
    # Store memory
    # ------------------------------
    async def store(
        self,
        key_namespace: tuple,
        task: str,
        memory: BaseModel 
    ):
        async with self.lock:
            await self.store_memory(key_namespace, task, memory)
            await self.add_embeddings(key_namespace, task, memory)                
            logger.debug(f"Stored memory for {agent} in session {session_id}")

    # ------------------------------------------------------------------
    # Episodic Memory
    # ------------------------------------------------------------------
    async def store_memory(
        self, 
        key_namespace: tuple,
        task: str, 
        memory: Union[Dict, BaseModel, EpisodicMemory]
    ):
        """Store episodic memory"""
        async with self.lock:
            if isinstance(memory, dict):
                episodic_memory = EpisodicMemory(
                    key_namespace=key_namespace,
                    task=task,
                    summary=memory
                )
            if self.episodic_adapter:
                await self.episodic_adapter.store_memory(episodic_memory)
            else: # In-memory Fallback
                episodic_memory = EpisodicMemory(
                    task=task,
                    summary=memory
                )
                # episodic_memory = memory.dict()
                self.in_memory_episodic[key_namespace].append(episodic_memory)
            logger.debug(f"Stored episodic memory for {agent} at stage {stage} in session {session_id}")


    # ------------------------------
    # Fetch episodic memory
    # ------------------------------
    async def fetch_memory(
        self,
        key_namespace: tuple,
        top_k: int = 3,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            # Adaptger
            if self.episodic_adapter:
                return await self.episodic_adapter.fetch_memory(
                    key_namespace=key_namespace,
                    filters=filters,
                    top_k=top_k,
                    limit=limit
                )
            else:
            # In-memory Fallback
                mems = []

                mems = self.in_memory_episodic[key_namespace].get(agent, [])

                # Now let's break the key namespace into individual keys for filtering
                session_id=key_namespace[1]
                agent=key_namespace[2]
                stage=key_namespace[3]
                namespace=key_namespace[4]

                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]

                '''
                if agent:
                    mems = self.in_memory_episodic[key_namespace].get(agent, [])
                else:
                    mems = [m for a in self.in_memory_episodic[session_id].values() for m in a]
                if stage:
                    if isinstance(stage, str):
                        mems = [m for m in mems if m.get("stage") == stage]
                    else:  # list
                        mems = [m for m in mems if m.get("stage") in stage]
                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]
                '''

                return mems[-top_k:]

    # ------------------------------------------------------------------
    # Semantic Store Embedding
    # ------------------------------------------------------------------

    async def add_embeddings(
        self, 
        key_namespace: tuple,
        task: str,
        memory: Union[Dict, BaseModel, SemanticMemory]
    ):
        """Store semantic memory"""
        async with self.lock:
            if isinstance(memory, dict):
                semantic_memory = SemanticMemory(
                    key_namespace=key_namespace,
                    task=task, 
                    summary=memory
                )
            if self.semantic_adapter:
                await self.semantic_adapter.add_embeddings(semantic_memory)
            else: # In-memory Fallback 
                semantic_memory = SemanticMemory( 
                    task=task, 
                    summary=memory
                )
                #mem = memory.dict()
                self.in_memory_semantic[key_namespace].append(semantic_memory)
            logger.debug(f"Stored semantic memory for {agent} in session {session_id}")


    # ------------------------------
    # Fetch semantic memory
    # ------------------------------

    async def semantic_search(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            # Adapter
            if self.semantic_adapter:
                return await self.semantic_adapter.semantic_search(
                    query=query,
                    top_k=top_k,
                    limit=limit,
                    filters=filters,
                )
            else: # In-memory fallback
                mems = []

                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]

                '''
                if agent:
                    mems = self.in_memory_semantic[session_id].get(agent, [])
                else:
                    mems = [m for a in self.in_memory_semantic[session_id].values() for m in a]
                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filter.items())]
                '''
                return mems[-top_k:]

    async def nl_to_sql(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            # Adapter
            if self.semantic_adapter:
                return await self.semantic_adapter.nl_to_sql(
                    query=query,
                    top_k=top_k,
                    limit=limit,
                    filters=filters,
                )
            else: # In-memory fallback
                mems = []

                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]

                '''
                if agent:
                    mems = self.in_memory_semantic[session_id].get(agent, [])
                else:
                    mems = [m for a in self.in_memory_semantic[session_id].values() for m in a]
                if filters:
                    mems = [m for m in mems if all(m.get(k) == v for k, v in filter.items())]
                '''
                return mems[-top_k:]
