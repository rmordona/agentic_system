from typing import Dict, Any
import requests
import numpy as np

from llm.embedding_factory import EmbeddingFactory
from llm.embeddings.base_client import BaseEmbeddingClient

# ------------------------------
# Cohere embedding client
# ------------------------------
class CohereEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, embed_model: str, api_key: str):
        import cohere
        self.embed_model = embed_model
        self.client = cohere.Client(api_key)

    def embed_text(self, text: str) -> list[float]:
        resp = self.client.embed(model=self.embed_model, texts=[text])
        return resp.embeddings[0]

# register dynamically
EmbeddingFactory.register("cohere", CohereEmbeddingClient)
