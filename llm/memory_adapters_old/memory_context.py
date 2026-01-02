"""
MemoryContext provides a scoped, immutable view over the MemoryManager.

It binds runtime dimensions (session, agent, stage, task, namespace)
into a stable, hashable key namespace and exposes a simple API for
storing and retrieving episodic and semantic memory.

MemoryContext contains NO storage logic.
All persistence, adapters, and backends are delegated to MemoryManager.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
# from llm.memory_manager import MemoryManager

class MemoryContext:
    def __init__(
        self,
        *,
        # memory_manager: MemoryManager,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        top_k: Optional[int] = None,
        limit: Optional[int] = None,
    ):

        # self.memory_manager = memory_manager
        self.namespace = namespace
        self.agent = agent
        self.top_k = top_k
        self.limit = limit

        # Dynamically updated during Agent.run()
        self.session_id = session_id
        self.stage = stage
        self.task = task

        # A new key_namespace will be formed as store key
        self.key_namespace = None

    # ----------------------------
    # Episodic store memory
    # ----------------------------

    '''
    async def store(self, memory):
        return await self.memory_manager.store( 
                key_namespace=self.key_namespace,  
                task=self.task, 
                memory=memory 
            )
    '''
    # ----------------------------
    # Episodic fetch memory
    # ----------------------------

    '''
    async def fetch_memory(
        self, 
        filters: Optional[Dict[str, Any]] = None, 
        top_k: Optional[int] = None,
        limit: Optional[int] = None
        ):
        return await self.memory_manager.fetch_memory(
            key_namespace=self.key_namespace,
            filters=filters,
            top_k=top_k or self.top_k,
            limit=limit or self.limit
        )
    '''
    # ----------------------------
    # Semantic memory
    # ----------------------------
    '''
    async def add_embeddings(self, embeddings, documents=None, metadatas=None):
        return await self.memory_manager.add_embeddings(
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            namespace=self.namespace
        ):
    '''
    '''
    async def semantic_search(
        self, 
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
        ):
        return await self.memory_manager.semantic_search(
            query=query,
            key_namespace=self.key_namespace,
            top_k=top_k or self.top_k,
            limit=limit or self.limit,
            filters=filters
        )

    async def query(
        self, 
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
        ):
        return await self.memory_manager.query(
            query=query,
            key_namespace=self.key_namespace,
            top_k=top_k or self.top_k,
            limit=limit or self.limit,
            filters=filters
        )
    '''
    # ----------------------------
    # Context scoping
    # ----------------------------
    def with_session(self, session_id: str) -> "MemoryContext":
        return MemoryContext(
            memory_manager=self.memory_manager,
            namespace=self.namespace,
            session_id=session_id,
            agent=self.agent,
            stage=self.stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_stage(self, stage: str) -> "MemoryContext":
        return MemoryContext(
            memory_manager=self.memory_manager,
            namespace=self.namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_task(self, task: str) -> "MemoryContext":
        return MemoryContext(
            memory_manager=self.memory_manager,
            namespace=self.namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            task=task,
            top_k=self.top_k,
            limit=self.limit
        )

    def with_namespace(self, namespace: str) -> "MemoryContext":
        return MemoryContext(
            memory_manager=self.memory_manager,
            namespace=namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            task=self.task,
            top_k=self.top_k,
            limit=self.limit
        )

    def generate_key_namespace(self)  -> "MemoryContext":
        self.key_namespace = (
                ("session_id",  self.session_id),
                ("agent",       self.agent),
                ("stage",       self.stage),
                ("namespace",   self.namespace) )
        return self
