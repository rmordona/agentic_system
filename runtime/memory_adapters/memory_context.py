from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from runtime.memory_manager import MemoryManager

class MemoryContext:
    def __init__(
        self,
        *,
        memory_manager: MemoryManager,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        top_k: int = 5,
        limit: int = 5,
    ):
        self.memory_manager = memory_manager
        self.namespace = namespace
        self.session_id = session_id
        self.agent = agent
        self.stage = stage
        self.task = task
        self.top_k = top_k
        self.limit = limit

    # ----------------------------
    # Episodic memory
    # ----------------------------
    async def store_episodic(self, memory):
        return await self.memory_manager.store_episodic(
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            memory=memory
        )

    async def fetch_episodic(self, filters: Optional[Dict[str, Any]] = None, top_k: Optional[int] = None):
        return await self.memory_manager.fetch_episodic(
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            filters=filters,
            top_k=top_k or self.top_k
        )

    # ----------------------------
    # Semantic memory
    # ----------------------------
    async def store_semantic(self, memory):
        return await self.memory_manager.store_semantic(
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            memory=memory
        )

    async def fetch_semantic(self, filters: Optional[Dict[str, Any]] = None, top_k: Optional[int] = None):
        return await self.memory_manager.fetch_semantic(
            session_id=self.session_id,
            agent=self.agent,
            task=self.task,
            filters=filters,
            top_k=top_k or self.top_k
        )

    async def query(self, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None):
        return await self.memory_manager.query(
            query=query,
            namespace=self.namespace,
            session_id=self.session_id,
            agent=self.agent,
            stage=self.stage,
            task=self.task,
            top_k=top_k or self.top_k,
            filter=filters
        )

    async def add_embeddings(self, *, ids, embeddings, documents=None, metadatas=None):
        return await self.memory_manager.add_embeddings(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            namespace=self.namespace
        )

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
