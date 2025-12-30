import asyncio
from collections import defaultdict
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
from runtime.memory_adapters.base import MemoryAdapter
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
        logger = AgentLogger.get_logger(None, component="memory_manager")

    # ------------------------------
    # Store memory
    # ------------------------------
    async def store(
        self,
        session_id: str,
        agent: str,
        stage: str,
        memory: BaseModel,
        semantic: bool = True,
        episodic: bool = True,
    ):
        async with self.lock:
            if episodic:
                if self.episodic_adapter:
                    await self.episodic_adapter.store_memory(memory)
                else:
                    self.in_memory_episodic[session_id][agent].append(memory.dict())
            if semantic:
                if self.semantic_adapter:
                    await self.semantic_adapter.store_memory(memory)
                else:
                    self.in_memory_semantic[session_id][agent].append(memory.dict())
            logger.debug(f"Stored memory for {agent} in session {session_id}")


    # ------------------------------------------------------------------
    # Semantic Memory
    # ------------------------------------------------------------------
    async def store_semantic(self, session_id: str, agent: str, memory: Union[Dict, SemanticMemory]):
        """Store semantic memory"""
        async with self.lock:
            if isinstance(memory, dict):
                memory = SemanticMemory(**memory)
            if self.semantic_adapter:
                await self.semantic_adapter.store_memory(memory)
            else:
                self.semantic_memory[session_id][agent].append(memory.dict())
            logger.debug(f"Stored semantic memory for {agent} in session {session_id}")


    # ------------------------------------------------------------------
    # Episodic Memory
    # ------------------------------------------------------------------
    async def store_episodic(self, session_id: str, agent: str, stage: str, memory: Union[Dict, EpisodicMemory]):
        """Store episodic memory"""
        async with self.lock:
            if isinstance(memory, dict):
                memory = EpisodicMemory(session_id=session_id, task=memory.get("task", ""), agent=agent, stage=stage, summary=memory)
            if self.episodic_adapter:
                await self.episodic_adapter.store_memory(memory)
            else:
                mem = memory.dict()
                self.episodic_memory[session_id][agent].append(mem)
            logger.debug(f"Stored episodic memory for {agent} at stage {stage} in session {session_id}")


    # ------------------------------
    # Fetch episodic memory
    # ------------------------------
    async def fetch_episodic(
        self,
        session_id: str,
        agent: Optional[str] = None,
        stage: Optional[Union[str, List[str]]] = None,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            if self.episodic_adapter:
                return await self.episodic_adapter.fetch_memory(
                    session_id=session_id,
                    agent=agent,
                    stage=stage,
                    task=filters.get("task") if filters else None,
                )
            # In-memory fallback
            mems = []
            if agent:
                mems = self.in_memory_episodic[session_id].get(agent, [])
            else:
                mems = [m for a in self.in_memory_episodic[session_id].values() for m in a]
            if stage:
                if isinstance(stage, str):
                    mems = [m for m in mems if m.get("stage") == stage]
                else:  # list
                    mems = [m for m in mems if m.get("stage") in stage]
            if filters:
                mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]
            return mems[-top_k:]

    # ------------------------------
    # Fetch semantic memory
    # ------------------------------
    async def fetch_semantic(
        self,
        session_id: str,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with self.lock:
            if self.semantic_adapter:
                return await self.semantic_adapter.fetch_memory(
                    session_id=session_id,
                    agent=agent,
                    task=task,
                    stage=filters.get("stage") if filters else None,
                )
            # In-memory fallback
            mems = []
            if agent:
                mems = self.in_memory_semantic[session_id].get(agent, [])
            else:
                mems = [m for a in self.in_memory_semantic[session_id].values() for m in a]
            if filters:
                mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]
            return mems[-top_k:]
