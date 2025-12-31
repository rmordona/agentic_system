from pathlib import Path
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class LocalMemoryStore:
    """
    Production-grade local memory store with TF-IDF search.
    Supports both semantic-ish search and persistent storage.
    """

    def __init__(self, workspace_name: str, persist_path: Path = None):
        self.workspace_name = workspace_name
        self.persist_path = persist_path
        self.data = []  # List of {"text": str, "metadata": dict}
        self.vectorizer = TfidfVectorizer()
        self.embeddings = None

        if persist_path and persist_path.exists():
            self.load()

    # -----------------------------
    # Storage
    # -----------------------------

    def add(self, text: str, metadata: dict = None):
        self.data.append({"text": text, "metadata": metadata or {}})
        self._update_embeddings()
        if self.persist_path:
            self.save()

    def _update_embeddings(self):
        if self.data:
            corpus = [d["text"] for d in self.data]
            self.embeddings = self.vectorizer.fit_transform(corpus)
        else:
            self.embeddings = None

    def save(self):
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def load(self):
        with open(self.persist_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._update_embeddings()

    # -----------------------------
    # Search
    # -----------------------------

    def search(self, query: str, top_k: int = 5):
        if not self.embeddings or not self.data:
            return []

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.embeddings).flatten()
        top_indices = sims.argsort()[::-1][:top_k]

        return [self.data[i] for i in top_indices if sims[i] > 0]

    async def asearch(self, query: str, top_k: int = 5):
        if not self.embeddings or not self.data:
            return []

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.embeddings).flatten()
        top_indices = sims.argsort()[::-1][:top_k]

        return [self.data[i] for i in top_indices if sims[i] > 0]

