# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/memory_manager.py
#
# Description:
#   MemoryManager handles semantic and episodic memories with:
#     - Automatic embedding
#     - Reward-based persistence
#     - Memory decay & summarization hooks
#     - Store-agnostic design
#
# NOTE:
#   - No factory logic
#   - No config loading
#   - No self-reflection (handled by ModelManager)
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Any, List
from statistics import mean
from datetime import datetime

from runtime.logger import AgentLogger
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.stores.base_store import EpisodicStore, SemanticStore

class MemoryManager:
    """
    Production-grade MemoryManager.

    Responsibilities:
      - Store & retrieve semantic (vector) memories
      - Store & retrieve episodic memories
      - Track rewards & update metadata
      - Trigger decay / summarization via store hooks

    Does NOT:
      - Load configs
      - Instantiate stores
      - Call LLMs
    """

    def __init__(
        self,
        embedding_client: BaseEmbeddingClient,
        eposidic_store: EpisodicStore,
        semantic_store: SemanticStore,
        summarize_after: int = 50,
        decay_after: int = 100,
    ):
        self.semantic_store = semantic_store
        self.episodic_store = episodic_store
        self.embedding_client = embedding_client

        self.summarize_after = summarize_after
        self.decay_after = decay_after

        # Reward tracking (in-memory, lightweight)
        self._reward_cache: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # Semantic Memory
    # ------------------------------------------------------------------
    async def save_semantic(
        self,
        key: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        reward: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Save semantic memory:
        - Automatically embeds text
        - Tracks reward
        - Triggers decay/summarization
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

        await self.semantic_store.save(key, entry, ttl_seconds)

        if reward is not None:
            self._reward_cache.setdefault(key, []).append(reward)
            await self._update_reward_stats(key)

        await self._maybe_decay(key)

        return entry

    async def retrieve_semantic(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantic memories via vector similarity.
        """
        vector = self.embedding_client.embed_text(query)

        return await self.semantic_store.similarity_search(
            vector=vector,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )

    # ------------------------------------------------------------------
    # Episodic Memory
    # ------------------------------------------------------------------
    async def save_episode(
        self,
        key: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ):
        """
        Save raw episodic memory (no embeddings).
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
        Fetch episodic memories.
        """
        return await self.episodic_store.query(
            top_k=top_k,
            metadata_filter=metadata_filter,
        )

    # ------------------------------------------------------------------
    # Reward Management
    # ------------------------------------------------------------------
    async def _update_reward_stats(self, key: str):
        rewards = self._reward_cache.get(key)
        if not rewards:
            return

        await self.semantic_store.update_metadata(
            key,
            {
                "avg_reward": mean(rewards),
                "reward_count": len(rewards),
            },
        )

    # ------------------------------------------------------------------
    # Decay / Summarization
    # ------------------------------------------------------------------
    async def _maybe_decay(self, key: str):
        """
        Delegates decay/summarization to the store if supported.
        """
        try:
            stats = await self.semantic_store.stats(key)
        except Exception:
            return

        if stats.get("count", 0) >= self.decay_after:
            try:
                await self.semantic_store.summarize(key)
            except Exception as e:
                AgentLogger.warn(f"Summarization failed for {key}: {e}")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    async def clear_all(self):
        await self.semantic_store.clear()
        await self.episodic_store.clear()

    async def count_semantic(self) -> int:
        return await self.semantic_store.count()

    async def count_episodic(self) -> int:
        return await self.episodic_store.count()
