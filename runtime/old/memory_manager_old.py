from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from collections import defaultdict
from pydantic import BaseModel
from runtime.memory_adapters.base import MemoryAdapter
from runtime.logger import AgentLogger


class MemoryManager:
    """
    Handles episodic and semantic memory per session and agent.
    Supports:
    - Multi-agent
    - Multi-session
    - Top-K retrieval
    """

    # Inherit the logger
    logger = None

    def __init__(self):
        # {session_id: {agent: [memory]}}
        self.semantic_memory: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self.episodic_memory: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self.lock = asyncio.Lock()


        # Bind workspace logger ONCE
        if MemoryManager.logger is None:
            MemoryManager.logger = AgentLogger.get_logger(None, component="memory_manager")

        logger = MemoryManager.logger

    # ------------------------------
    # Semantic Memory
    # ------------------------------
    async def store_semantic(self, session_id: str, agent: str, memory: Dict[str, Any]):
        async with self.lock:
            self.semantic_memory[session_id][agent].append(memory)
            logger.debug(f"Stored semantic memory for {agent} in session {session_id}")

    async def fetch_semantic(
        self, session_id: str, task: str, agent: Optional[str] = None, top_k: int = 5, filters: Optional[Dict] = None
    ) -> List[Dict]:
        async with self.lock:
            agent_memories = (
                self.semantic_memory[session_id][agent] if agent else [m for a in self.semantic_memory[session_id].values() for m in a]
            )
            # Apply filters
            if filters:
                agent_memories = [m for m in agent_memories if all(m.get(k) == v for k, v in filters.items())]
            return agent_memories[-top_k:]

    # ------------------------------
    # Episodic Memory
    # ------------------------------
    async def store_episodic(self, session_id: str, agent: str, stage: str, memory: Dict[str, Any]):
        async with self.lock:
            mem = memory.copy()
            mem["stage"] = stage
            self.episodic_memory[session_id][agent].append(mem)
            logger.debug(f"Stored episodic memory for {agent} at stage {stage} in session {session_id}")

    async def fetch_episodic(
        self, session_id: str, agent: str, stage: Optional[str] = None, top_k: int = 3, filters: Optional[Dict] = None
    ) -> List[Dict]:
        async with self.lock:
            mems = self.episodic_memory[session_id].get(agent, [])
            if stage:
                mems = [m for m in mems if m.get("stage") == stage]
            if filters:
                mems = [m for m in mems if all(m.get(k) == v for k, v in filters.items())]
            return mems[-top_k:]

    # ------------------------------
    # Generic Store
    # ------------------------------
    async def store(self, session_id: str, agent: str, stage: str, output: Dict[str, Any]):
        await self.store_semantic(session_id, agent, output)
        await self.store_episodic(session_id, agent, stage, output)


