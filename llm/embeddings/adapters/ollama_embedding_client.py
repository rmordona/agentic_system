# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/adapters/ollama_embedding_client.py
#
# Description:
#   Ollama embedding client adapter for LangGraph/InMemoryStore integration.
#   Features:
#     - Uses Ollama local API `/api/embed` with "input" field
#     - Returns validated embedding vectors for LangGraph semantic search
#     - Synchronous function compatible with LangGraph thread pool
#     - Handles HTTP errors and empty embeddings gracefully
#     - Logs vector dimension and errors for debugging
#
# Usage:
#   client = OllamaEmbeddingClient(
#       model_name="nomic-embed-text:latest",
#       endpoint="http://localhost:11434/api/embed"
#   )
#   vector = client.embed_text("The sky is blue.")  # returns List[float] of 768 dims
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-04
# -----------------------------------------------------------------------------

from typing import List, Optional
import httpx
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class OllamaEmbeddingClient:
    """
    Ollama embedding client for generating semantic vectors via /api/embed.
    """

    def __init__(
        self,
        model_name: str,
        endpoint: str,
        models: Optional[List[str]] = None,
        api_key: Optional[str] = None
    ):
        """
        Args:
            model_name: Ollama embedding model name (must support embeddings)
            endpoint: URL of the Ollama embedding API (e.g., http://localhost:11434/api/embed)
            models: optional list of allowed model names for validation
            api_key: optional API key if server is secured
        """
        if not model_name:
            raise ValueError("model_name must be provided")

        if models and model_name not in models:
            raise ValueError(f"Model {model_name} is not in the supported list: {models}")

        self.model_name = model_name
        self.endpoint = endpoint
        self.models = models
        self.api_key = api_key

        logger.info(f"OllamaEmbeddingClient initialized with model '{model_name}' at {endpoint}")

    # ------------------------------------------------------------------
    # Embedding API
    # ------------------------------------------------------------------
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.

        Args:
            text: input text to embed

        Returns:
            List[float]: embedding vector

        Raises:
            RuntimeError if embedding fails or is empty
        """
        if not text:
            raise ValueError("Cannot embed empty text")

        payload = {"model": self.model_name, "input": text}

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = httpx.post(self.endpoint, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
        except httpx.RequestError as e:
            raise RuntimeError(f"Embedding request failed for text='{text[:50]}...': {e}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Embedding request returned HTTP {e.response.status_code} for text='{text[:50]}...'")

        data = resp.json()

        embedding = data.get("embeddings", [[]])[0]

        logger.info(f"Sending Vector -> Length of Dimension: {len(embedding)}")

        if not embedding:
            raise RuntimeError(f"Model '{self.model_name}' returned empty embedding for text='{text[:50]}...'")

        return embedding
