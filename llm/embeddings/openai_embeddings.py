from typing import Dict, Any
import requests
import numpy as np

from llm.embeddings.embedding_factory import EmbeddingFactory
from llm.embeddings.base_client import BaseEmbeddingClient

# ------------------------------
# OpenAI embedding client
# ------------------------------
class OpenAIEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, embed_model: str, api_key: str):
        import openai
        self.embed_model = embed_model
        openai.api_key = api_key

    def embed_text(self, text: str) -> list[float]:
        import openai
        resp = openai.Embedding.create(
            input=text,
            model=self.embed_model
        )
        return resp.data[0].embedding


# register dynamically
EmbeddingFactory.register("openai", OpenAIEmbeddingClient)
