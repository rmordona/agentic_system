from typing import Dict, Any
import requests
import numpy as np

from llm.embeddings.embedding_factory import EmbeddingFactory
from llm.embeddings.base_client import BaseEmbeddingClient

# ------------------------------
# Ollama embedding client
# ------------------------------
class OllamaEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model

    def embed_text(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "prompt": text,
            "stream": False,
            "options": {"num_predict": 0},  # not used for embeddings
        }
        resp = requests.post(f"{self.endpoint}", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("embeddings", [])


# register dynamically
EmbeddingFactory.register("ollama", OllamaEmbeddingClient)

