# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/ollama_embeddings.py
#
# Description:
#   Ollama embedding client implementation using httpx.
#   Supports both synchronous and asynchronous embedding generation.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

from typing import Optional, List
import httpx

from llm.embeddings.adapters.base_client import BaseEmbeddingClient
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class OllamaEmbeddingClient(BaseEmbeddingClient):
    """
    Ollama embedding client using httpx.

    Supports:
    - Sync embeddings (embed_text)
    - Async embeddings (aembed_text)
    """

    def __init__(
        self,
        model_name: str,
        endpoint: str,
        embed: Optional[str] = None,
        models: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        if not model_name:
            raise ValueError("Model Name must be provided for embeddings.")

        if models and model_name not in models:
            raise ValueError(
                f"Model Name '{model_name}' is not in supported list {models}"
            )

        self.model_name = model_name
        self.endpoint = endpoint
        self.embed = embed
        self.models = models
        self.api_key = api_key
        self.timeout = timeout

        logger.info("OllamaEmbeddingClient initialized")

    # ------------------------------------------------------------------
    # Sync embedding (blocking)
    # ------------------------------------------------------------------
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings synchronously.
        Safe for non-async code paths.
        """

        payload = {
            "model": self.model_name,
            "prompt": text,
            "stream": False,
            "options": {"num_predict": 0},
        }

        logger.debug("Generating embeddings (sync)")

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        embedding = data.get("embedding", [])

        if not embedding:
            logger.warning("Empty embedding returned from Ollama")

        return embedding

    # ------------------------------------------------------------------
    # Async embedding (non-blocking)
    # ------------------------------------------------------------------
    async def aembed_text(self, text: str) -> List[float]:
        """
        Generate embeddings asynchronously.
        Preferred for agentic workflows.
        """

        payload = {
            "model": self.model_name,
            "prompt": text,
            "stream": False,
            "options": {"num_predict": 0},
        }

        logger.debug("Generating embeddings (async)")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        embedding = data.get("embedding", [])

        if not embedding:
            logger.warning("Empty embedding returned from Ollama")

        return embedding
