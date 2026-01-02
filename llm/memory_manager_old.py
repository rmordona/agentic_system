"""
MemoryManager is the central authority for all memory operations.

It selects adapters, coordinates concurrency, and enforces storage
semantics for episodic and semantic memory. It is backend-agnostic and
supports both persistent adapters and in-memory fallbacks.

MemoryManager does NOT understand agents, stages, or prompts —
it only stores and retrieves memory via structured keys.
"""

import asyncio
from collections import defaultdict
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
from langmem.knowledge.extraction import  MemoryStoreManager

from llm.memory_adapters.base import MemoryAdapter
from llm.memory_adapters.memory_factory import MemoryFactory
from llm.memory_schemas import EpisodicMemory, SemanticMemory

from llm.embeddings.base import EmbeddingStore
from llm.embeddings.embedding_factory import EmbeddingFactory 
#from llm.llm_manager import LLMManager 




from runtime.logger import AgentLogger

class MemoryManager:
    """
    Fully pluggable memory manager:
    - episodic: MemoryAdapter
    - semantic: MemoryAdapter
    """

    def __init__(self, 
        store_config: Dict[str, Any],
        # store_manager:  MemoryStoreManager
        #llm_manager: LLMManager,
        #embedding_store: EmbeddingStore
        ):
        self.lock = asyncio.Lock()
        #self.episodic_adapter = episodic
        #self.semantic_adapter = semantic
        self.in_memory_episodic: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self.in_memory_semantic: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

        self.dsn                = store_config.get("dsn", None)  # Data Source Name
        self.persist_directory  = store_config.get("persist_directory", None)
        self.collections        = store_config.get("collections", None)
        self.embedding_model    = store_config.get("embedding_model", None)
        self.dims               = store_config.get("dims", None),  

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(None, component="system")

        logger.info("Bootstrapping LLM ...")
        logger.info(f" Data Source Name: {self.dsn}")
        logger.info(f" Persisten Directory: {self.persist_directory}")
        logger.info(f" Collections: {self.collections}")
        logger.info(f" Embedding Model: {self.embedding_model}")
        logger.info(f" Dim: {self.dims}")



        self.episodic_adapter = MemoryFactory.get_episodic_adapter(
            config["episodic"]
        )
        self.semantic_adapter = MemoryFactory.get_semantic_adapter(
            config["semantic"],
            llm_manager=llm_manager,
            embedding_store=embedding_store,
        )

        #embedding_config = self.config.get("embeddings", {})
        self.embedding_store = EmbeddingFactory.build(config=embedding_config, logger=self.logger)

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
        key_namespace: tuple,
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

    async def query(
        self,
        query: str, 
        key_namespace: tuple,
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            # Adapter
            if self.semantic_adapter:
                return await self.semantic_adapter.query(
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
