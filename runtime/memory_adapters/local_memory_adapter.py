# runtime/memory_adapters/local_memory.py

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from runtime.memory_adapters.base import MemoryAdapter
import json
import uuid

class LocalMemoryAdapter(MemoryAdapter):
    """
    Local in-memory memory adapter.
    Supports episodic and semantic-ish memory.
    Persistent JSON storage optional.
    """

    def __init__(self, workspace_name: str, persist_path: Optional[Path] = None):
        self.workspace_name = workspace_name
        self.persist_path = persist_path
        self._memory: List[Dict[str, Any]] = []
        self._vectorizer = TfidfVectorizer()
        self._embeddings = None

        if persist_path and persist_path.exists():
            self._load_from_disk()

    # -----------------------------------------------------------------
    # Core storage
    # -----------------------------------------------------------------

    async def store_memory(self, memory: BaseModel) -> str:
        mem_dict = memory.dict()
        mem_dict["_id"] = str(uuid.uuid4())
        self._memory.append(mem_dict)
        self._update_embeddings()
        if self.persist_path:
            self._save_to_disk()
        return mem_dict["_id"]

    async def fetch_memory(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        task: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch memory objects filtered by session, agent, stage, task, or additional filters.
        If 'filters' contains a 'query' key, performs TF-IDF similarity search.
        """
        results = self._memory

        # Apply standard filters
        if session_id:
            results = [m for m in results if m.get("session_id") == session_id]
        if agent:
            results = [m for m in results if m.get("agent") == agent]
        if stage:
            results = [m for m in results if m.get("stage") == stage]
        if task:
            results = [m for m in results if m.get("task") == task]
        if filters:
            for k, v in filters.items():
                if k != "query":
                    results = [m for m in results if m.get(k) == v]

        # Semantic-ish search using TF-IDF
        query_text = filters.get("query") if filters else None
        if query_text and results:
            corpus = [m["text"] for m in results if "text" in m]
            if corpus:
                vecs = self._vectorizer.fit_transform(corpus)
                query_vec = self._vectorizer.transform([query_text])
                sims = cosine_similarity(query_vec, vecs).flatten()
                top_indices = sims.argsort()[::-1][:top_k]
                results = [results[i] for i in top_indices if sims[i] > 0]

        return results[:top_k] if top_k else results

    async def clear(self, session_id: Optional[str] = None):
        if session_id:
            self._memory = [m for m in self._memory if m.get("session_id") != session_id]
        else:
            self._memory = []
        self._update_embeddings()
        if self.persist_path:
            self._save_to_disk()

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _update_embeddings(self):
        corpus = [m["text"] for m in self._memory if "text" in m]
        if corpus:
            self._embeddings = self._vectorizer.fit_transform(corpus)
        else:
            self._embeddings = None

    def _save_to_disk(self):
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self._memory, f, indent=2)

    def _load_from_disk(self):
        with open(self.persist_path, "r", encoding="utf-8") as f:
            self._memory = json.load(f)
        self._update_embeddings()

