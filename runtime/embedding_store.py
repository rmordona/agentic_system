from __future__ import annotations
import asyncio
from typing import Any, Dict, List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from runtime.logger import AgentLogger


class EmbeddingStore:
    """
    Simple in-memory embedding store.
    Supports:
    - Multi-session embeddings
    - Top-K retrieval using cosine similarity
    """

    def __init__(self):
        # {session_id: {agent: [(embedding_vector, metadata)]}}
        self.store: Dict[str, Dict[str, List[Dict]]] = {}
        self.lock = asyncio.Lock()

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(None, component="embedding_store")

    async def add_embedding(self, session_id: str, agent: str, embedding: List[float], metadata: Dict[str, Any]):
        async with self.lock:
            self.store.setdefault(session_id, {}).setdefault(agent, [])
            self.store[session_id][agent].append({"vector": np.array(embedding), "metadata": metadata})
            logger.debug(f"Added embedding for {agent} in session {session_id}")

    async def search(self, session_id: str, query_vector: List[float], agent: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Returns top_k closest embeddings across all agents if agent=None
        """
        async with self.lock:
            results = []
            query_vec = np.array(query_vector).reshape(1, -1)
            agents_to_search = [agent] if agent else list(self.store.get(session_id, {}).keys())
            for a in agents_to_search:
                for entry in self.store.get(session_id, {}).get(a, []):
                    score = cosine_similarity(query_vec, entry["vector"].reshape(1, -1))[0][0]
                    results.append({"agent": a, "metadata": entry["metadata"], "score": score})
            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]


