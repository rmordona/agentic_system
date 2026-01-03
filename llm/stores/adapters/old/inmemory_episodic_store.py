# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/inmemory_episodic_store.py
#
# Description:
#   In-memory episodic store for time-ordered event memory.
#   No embeddings, no similarity search.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# -----------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from llm.stores.base import EpisodicStore


class InMemoryEpisodicStore(EpisodicStore):
    """
    In-memory episodic memory store.

    - Stores chronological events
    - No embeddings
    - No vector indexing
    - Optional TTL
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []

    # ------------------------------------------------------------------
    async def save(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        async with self._lock:
            expires_at = (
                time.time() + ttl_seconds if ttl_seconds else None
            )

            self._store[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": expires_at,
            }

            if key not in self._order:
                self._order.append(key)

    # ------------------------------------------------------------------
    async def fetch(
        self,
        key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            now = time.time()

            def valid(k: str) -> bool:
                entry = self._store.get(k)
                return (
                    entry
                    and (entry["expires_at"] is None or entry["expires_at"] > now)
                )

            keys = (
                [key] if key else list(reversed(self._order))
            )

            results = []
            for k in keys:
                if not valid(k):
                    continue
                results.append(
                    {
                        "key": k,
                        **self._store[k],
                    }
                )
                if len(results) >= limit:
                    break

            return results

    # ------------------------------------------------------------------
    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)
            if key in self._order:
                self._order.remove(key)

    # ------------------------------------------------------------------
    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            self._order.clear()

