# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/cohere_embeddings.py
#
# Description:
#   Cohere embedding client implementation.
#   Registers itself dynamically with EmbeddingFactory.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------
from typing import Dict, Any
import requests
import numpy as np

from llm.embeddings.adapters.base_client import BaseEmbeddingClient

# ------------------------------
# Cohere embedding client
# ------------------------------
class CohereEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, embed: str, endpoint: str, api_key: str):
        import cohere
        self.embed_model = embed
        self.client = cohere.Client(api_key)

    def embed_text(self, text: str) -> list[float]:
        resp = self.client.embed(model=self.embed_model, texts=[text])
        return resp.embeddings[0]
