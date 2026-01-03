# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/ollama_embeddings.py
#
# Description:
#   Ollama embedding client implementation.
#   Registers itself dynamically with EmbeddingFactory.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------
from typing import Dict, Any
import requests
import numpy as np

from llm.embeddings.base_client import BaseEmbeddingClient

# ------------------------------
# Ollama embedding client
# ------------------------------
class OllamaEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, embed: str, endpoint: str):
        self.endpoint = endpoint
        self.model = embed

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


