from pathlib import Path
import json
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Okapi


class LocalMemoryStore:
    """
    Production-grade local memory store with BM25 search.
    Supports semantic-ish search and optional persistence.
    """

    def __init__(
        self,
        workspace_name: str,
        persist_path: Optional[Path] = None,
        tokenizer=str.split,
    ):
        self.workspace_name = workspace_name
        self.persist_path = persist_path

        # Each entry: {"text": str, "metadata": dict}
        self.data: List[Dict[str, Any]] = []

        self.tokenizer = tokenizer
        self._bm25: Optional[BM25Okapi] = None
        self._corpus_tokens: List[List[str]] = []

        if persist_path and persist_path.exists():
            self.load()

    # -----------------------------
    # Storage
    # -----------------------------

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        entry = {
            "text": text,
            "metadata": metadata or {},
        }
        self.data.append(entry)

        tokens = self.tokenizer(text.lower())
        self._corpus_tokens.append(tokens)

        self._rebuild_index()

        if self.persist_path:
            self.save()

    def _rebuild_index(self):
        if self._corpus_tokens:
            self._bm25 = BM25Okapi(self._corpus_tokens)
        else:
            self._bm25 = None

    def save(self):
        if not self.persist_path:
            return

        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def load(self):
        with open(self.persist_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self._corpus_tokens = [
            self.tokenizer(entry["text"].lower()) for entry in self.data
        ]
        self._rebuild_index()

    # -----------------------------
    # Search
    # -----------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        if not self._bm25 or not self.data:
            return []

        query_tokens = self.tokenizer(query.lower())
        scores = self._bm25.get_scores(query_tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )

        results = []
        for idx, score in ranked[:top_k]:
            if score > min_score:
                results.append(self.data[idx])

        return results

    async def asearch(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        # Async wrapper for LangMem compatibility
        return self.search(query=query, top_k=top_k, min_score=min_score)

