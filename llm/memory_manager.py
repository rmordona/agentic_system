# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/memory_manager.py
#
# Description:
#   MemoryManager provides a unified interface for managing both semantic
#   and episodic memories within the Agentic System. It is store-agnostic
#   and integrates with a BaseEmbeddingClient for vector embeddings.
#
#   Features:
#     - Save, retrieve, search, and delete semantic memories
#     - Save and fetch episodic (raw) memories
#     - Reward tracking and metadata aggregation
#     - Automatic decay and summarization hooks for long-term memory
#     - Store-agnostic: works with any BaseStore implementation
#     - Async-friendly operations for high-performance agents
#
# Usage:
#   from llm.memory_manager import MemoryManager
#   from llm.stores.adapters.inmemory_store import InMemoryStore
#   from llm.embeddings.adapters.openai_client import OpenAIEmbeddingClient
#
#   store = InMemoryStore()
#   embeddings = OpenAIEmbeddingClient()
#   memory_manager = MemoryManager(
#       embedding_client=embeddings,
#       store=store,
#       summarize_after=50,
#       decay_after=100
#   )
#
#   # Save a semantic memory
#   await memory_manager.save_semantic(
#       namespace=("user_123", "interactions"),
#       key="last_query",
#       text="Explain agentic systems in a paragraph.",
#       metadata={"topic": "ai_systems"},
#       reward=0.9
#   )
#
#   # Retrieve top semantic memories
#   results = await memory_manager.retrieve_semantic(
#       namespace=("user_123", "interactions"),
#       query="agentic systems",
#       top_k=5
#   )
#
#   # Save an episodic memory
#   await memory_manager.save_episode(
#       namespace=("user_123", "sessions"),
#       key="session_001",
#       data={"messages": ["Hello", "How are you?"]}
#   )
#
#   # Fetch episodic memories
#   episodes = await memory_manager.fetch_episodes(
#       namespace=("user_123", "sessions")
#   )
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-04
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from statistics import mean
from datetime import datetime

from runtime.logger import AgentLogger
from llm.embeddings.adapters.base_client import BaseEmbeddingClient
from llm.stores.adapters.base_store import BaseStore

logger = AgentLogger.get_logger(component="system")


class MemoryManager:
    """
    MemoryManager for unified episodic + semantic memory store.
    """

    def __init__(
        self,
        embedding_client: BaseEmbeddingClient,
        store: BaseStore,
        summarize_after: int = 50,
        decay_after: int = 100,
    ):
        self.embedding_client = embedding_client
        self.store = store
        self.summarize_after = summarize_after
        self.decay_after = decay_after
        self._reward_cache: Dict[str, List[float]] = {}

        logger.info("Memory Manager initialized")

    # ------------------------------------------------------------------
    # Semantic Memory
    # ------------------------------------------------------------------
    async def save_semantic(
        self,
        namespace: Tuple[str, str],
        key: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None,
        reward: Optional[float] = None,
    ) -> Dict[str, Any]:

        entry = {
            "text": text,
            "metadata": metadata or {},
            "document": document or {},
            "reward": reward,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info("Saving Semantics ...")

        # unified store API: semantic=True triggers semantic index

        def _save_semantics():
            self.store.put(namespace, key, entry, semantic=True)

            logger.info("Saving Semantics completed")

        await asyncio.to_thread(_save_semantics)

        if reward is not None:
            self._reward_cache.setdefault(key, []).append(reward)
            await self._update_reward_stats(namespace, key)

        await self._maybe_decay(namespace, key)
    
        return entry

    async def retrieve_semantic(
        self,
        namespace: Tuple[str, str],
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantic memories using the store's semantic search.
        """
        return await self.store.search(namespace=namespace, query=query, limit=top_k, metadata_filter=metadata_filter)

    # ------------------------------------------------------------------
    # Episodic Memory
    # ------------------------------------------------------------------
    async def save_episode(
        self,
        namespace: Tuple[str, str],
        key: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None,
    ):
        """
        Save episodic memory (raw, key/value)
        """
        entry = {
            "value": data,
            "metadata": metadata or {},
            "document": document or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        # unified store API: semantic=False triggers raw storage
        await self.store.put(namespace, key, entry, semantic=False)

    async def fetch_episodes(
        self,
        namespace: Tuple[str, str],
        keys: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch episodic memories by exact key(s) within a namespace.

        Args:
            namespace: tuple like ("user_123", "sessions")
            keys: list of keys to fetch; if None, fetch all keys in the namespace
        """
        results = []

        if keys:
            # Fetch specific keys
            for key in keys:
                entry = await self.store.get(namespace, key, semantic=False)
                if entry:
                    results.append(entry)
        else:
            # Fetch all keys in the namespace
            all_keys = list(await self.store.keys(namespace))
            for key in all_keys:
                entry = await self.store.get(namespace, key, semantic=False)
                if entry:
                    results.append(entry)

        return results


    # ------------------------------------------------------------------
    # Reward Management
    # ------------------------------------------------------------------
    async def _update_reward_stats(self, namespace: Tuple[str, str], key: str):
        rewards = self._reward_cache.get(key)
        if not rewards:
            return
        # Update only the metadata part
        logger.info("Updating Rewards Stats ")
        current_entry = await self.store.get(namespace, key)
        if current_entry:
            current_entry.setdefault("metadata", {})
            current_entry["metadata"].update({
                "avg_reward": mean(rewards),
                "reward_count": len(rewards),
            })
            # Put back to store
            await self.store.put(namespace, key, current_entry, semantic=True)

    # ------------------------------------------------------------------
    # Decay / Summarization
    # ------------------------------------------------------------------
    async def _maybe_decay(self, namespace: Tuple[str, str], key: str):
        try:
            logger.info("Also trying to perform Memory decay and summarization")
            if hasattr(self.store, "stats"):
                stats = await self.store.stats(namespace, key)
                if stats.get("count", 0) >= self.decay_after and hasattr(self.store, "summarize"):
                    await self.store.summarize(namespace, key)
        except Exception as e:
            logger.warning(f"Decay/summarization failed for {key}: {e}")
    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    async def clear_namespace(self, namespace: Tuple[str, str]):
        await self.store.clear_namespace(namespace)

    async def count_namespace(self, namespace: Tuple[str, str]) -> int:
        return await self.store.count_namespace(namespace)
