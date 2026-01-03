# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/openai_embeddings.py
#
# Description:
#   OpenAI embedding client implementation.
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
# OpenAI embedding client
# ------------------------------
class OpenAIEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, embed: str, endpoint: str, api_key: str):
        import openai
        self.embed_model = embed
        openai.api_key = api_key

    def embed_text(self, text: str) -> list[float]:
        import openai
        resp = openai.Embedding.create(
            input=text,
            model=self.embed_model
        )
        return resp.data[0].embedding
