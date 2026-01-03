# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/inmemory_semantic_store.py
#
# Description:
#   In-memory semantic store implementation using hnswlib for
#   approximate nearest neighbor (ANN) vector search with cosine similarity.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# -----------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import hnswlib
import time
from typing import Any, Dict, List, Optional

from llm.stores.base import SemanticStore


class InMemorySemanticStore(SemanticStore):
    """
    In-memory semantic store backed by hnswlib.

    - Uses cosine similarity
    - Fast ANN search
    - Non-persistent
    - Thread-safe via asyncio locks
    """

    def __init__(
        self,
        dim: int,
        max_elements: int = 10_000,
        ef_construction: int = 200,
        M: int = 16,
    ):
        self.dim = dim
        self.max_elements = max_elements

        self._index = hnswlib.Index(space="cosine", dim=dim)
        self._index.init_index(
            max_elements=max_elements,
            ef_construction=ef_construction,
            M=M,
        )
        self._index.set_ef(50)

        self._lock = asyncio.Lock()
        self._next_id = 0

        # Internal storage
        self._id_to_key: Dict[int, str] = {}
        self._key_to_id: Dict[str, int] = {}
        self._store: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    async def save(
        self,
        key: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        async with self._lock:
            if key in self._key_to_id:
                # Overwrite existing entry
                internal_id = self._key_to_id[key]
            else:
                internal_id = self._next_id
                self._next_id += 1

                self._key_to_id[key] = internal_id
                self._id_to_key[internal_id] = key

                self._index.add_items([embedding], [internal_id])

            expires_at = (
                time.time() + ttl_seconds if ttl_seconds else None
            )

            self._store[key] = {
                "text": text,
                "embedding": embedding,
                "metadata": metadata or {},
                "expires_at": expires_at,
            }

    # ------------------------------------------------------------------
    async def similarity_search(
        self,
        embedding: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            if not self._store:
                return []

            labels, distances = self._index.knn_query(
                [embedding], k=min(top_k, len(self._store))
            )

            results: List[Dict[str, Any]] = []

            for internal_id, distance in zip(labels[0], distances[0]):
                key = self._id_to_key.get(int(internal_id))
                if not key:
                    continue

                entry = self._store.get(key)
                if not entry:
                    continue

                # TTL check
                if entry["expires_at"] and entry["expires_at"] < time.time():
                    continue

                # Metadata filter
                if metadata_filter:
                    if not all(
                        entry["metadata"].get(k) == v
                        for k, v in metadata_filter.items()
                    ):
                        continue

                results.append(
                    {
                        "key": key,
                        "text": entry["text"],
                        "metadata": entry["metadata"],
                        "score": float(1 - distance),  # cosine similarity
                    }
                )

            return results

    # ------------------------------------------------------------------
    async def delete(self, key: str) -> None:
        async with self._lock:
            internal_id = self._key_to_id.pop(key, None)
            if internal_id is not None:
                self._id_to_key.pop(internal_id, None)
                self._store.pop(key, None)
                # NOTE: hnswlib does not support deletion;
                # stale vectors are ignored via metadata cleanup.

    # ------------------------------------------------------------------
    async def clear(self) -> None:
        async with self._lock:
            self._index = hnswlib.Index(space="cosine", dim=self.dim)
            self._index.init_index(max_elements=self.max_elements)
            self._id_to_key.clear()
            self._key_to_id.clear()
            self._store.clear()
            self._next_id = 0

