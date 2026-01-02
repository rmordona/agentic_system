# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/memory_manager.py
#
# Description:
#   MemoryManager handles semantic and episodic memories with:
#     - Reward-based persistence
#     - Automatic embedding
#     - Memory decay / summarization
#     - Self-reflection via LLM
#     - Multiple store support (Redis, Chroma, Postgres, InMemory, Oracle)
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Any, List
from statistics import mean
from datetime import datetime
import asyncio

from llm.embeddings.embedding_factory import EmbeddingFactory, BaseEmbeddingClient
from llm.stores.store_factory import BaseStore, StoreFactory
from runtime.logger import AgentLogger


class MemoryManager:
    """
    Production-grade MemoryManager that supports:
      - Semantic memories (vectorized)
      - Episodic memories (raw)
      - Automatic embedding via EmbeddingFactory
      - Reward tracking
      - Memory decay / summarization
    """

    def __init__(
        self,
        store_factory: StoreFactory,
        embedding_factory: EmbeddingFactory,
        semantic_store_name: str = "default",
        episodic_store_name: str = "default",
        summarize_after: int = 50,
        decay_after: int = 100,
    ):
        # Factories
        self.store_factory = store_factory
        self.embedding_factory = embedding_factory

        # Stores
        self.semantic_store: BaseStore = self.store_factory.get_store(semantic_store_name)
        self.episodic_store: BaseStore = self.store_factory.get_store(episodic_store_name)

        # Embedding client
        self.embedding_client: BaseEmbeddingClient = self.embedding_factory.get_embedding()

        # Decay / summarization thresholds
        self.summarize_after = summarize_after
        self.decay_after = decay_after

        # Reward cache
        self._reward_cache: Dict[str, List[float]] = {}

    # ----------------------------
    # Semantic Memory
    # ----------------------------
    async def save_semantic(
        self,
        key: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        reward: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Save semantic memory:
          - Auto-embed text
          - Attach metadata and reward
          - Trigger decay / summarization
          - Trigger self-reflection
        """
        vector = self.embedding_client.embed_text(text)
        entry = {
            "key": key,
            "text": text,
            "embedding": vector,
            "metadata": metadata or {},
            "reward": reward,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save
        await self.semantic_store.save(key, entry, ttl_seconds)

        # Update reward stats
        if reward is not None:
            self._reward_cache.setdefault(key, []).append(reward)
            await self._update_reward_stats(key)

        # Check for decay / summarization
        await self._maybe_decay(key)

        # Self-reflection
        await self._self_reflect(key, text)

        return entry

    async def retrieve_semantic(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-K relevant semantic memories by embedding similarity.
        """
        vector = self.embedding_client.embed_text(query)
        results = await self.semantic_store.similarity_search(
            vector=vector,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
        return results

    # ----------------------------
    # Episodic Memory
    # ----------------------------
    async def save_episode(
        self,
        key: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Save a raw episodic memory.
        """
        entry = {
            "key": key,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.episodic_store.save(key, entry, ttl_seconds)

    async def fetch_episodes(
        self,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch episodic memories optionally filtered by metadata.
        """
        return await self.episodic_store.query(top_k=top_k, metadata_filter=metadata_filter)

    # ----------------------------
    # Reward Management
    # ----------------------------
    async def _update_reward_stats(self, key: str):
        rewards = self._reward_cache.get(key, [])
        if not rewards:
            return
        avg_reward = mean(rewards)
        await self.semantic_store.update_metadata(key, {"avg_reward": avg_reward, "count": len(rewards)})

    # ----------------------------
    # Decay / Summarization
    # ----------------------------
    async def _maybe_decay(self, key: str):
        stats = await self.semantic_store.stats(key)
        if stats.get("count", 0) >= self.decay_after:
            await self.semantic_store.summarize(key)

    # ----------------------------
    # Utilities
    # ----------------------------
    async def clear_all(self) -> None:
        await self.semantic_store.clear()
        await self.episodic_store.clear()

    async def count_semantic(self) -> int:
        return await self.semantic_store.count()

    async def count_episodic(self) -> int:
        return await self.episodic_store.count()
