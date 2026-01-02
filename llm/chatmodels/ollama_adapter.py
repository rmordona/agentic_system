# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/adapters/ollama_adapter.py
#
# Description:
#   Hardened Ollama adapter supporting chat, generate, and embeddings APIs.
#   Provides a normalized interface over Ollama's heterogeneous payloads
#   and response formats.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-02
# -----------------------------------------------------------------------------

from __future__ import annotations

import httpx
import asyncio
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Normalized response objects
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    content: str
    raw: Dict[str, Any]
    usage: Dict[str, int]
    model: str


@dataclass
class EmbeddingResponse:
    embeddings: List[float]
    model: str
    raw: Dict[str, Any]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OllamaError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Ollama Adapter
# ---------------------------------------------------------------------------

class OllamaAdapter:
    """
    Hardened Ollama API adapter.

    Supported APIs:
      - /api/chat       (messages-based)
      - /api/generate   (prompt-based)
      - /api/embeddings (embedding generation)

    This adapter:
      - Normalizes payloads
      - Normalizes responses
      - Handles retries and timeouts
      - Avoids LangChain abstractions
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_max_tokens: int = 512,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_max_tokens = default_max_tokens

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    async def _post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.5 * attempt)

        raise OllamaError(f"Ollama request failed: {last_error}")

    # ------------------------------------------------------------------
    # Chat API (/api/chat)
    # ------------------------------------------------------------------

    async def chat(
        self,
        *,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens or self.default_max_tokens,
            },
        }

        if temperature is not None:
            payload["options"]["temperature"] = temperature

        raw = await self._post("/api/chat", payload)

        content = raw.get("message", {}).get("content", "")
        usage = {
            "prompt_tokens": raw.get("prompt_eval_count", 0),
            "completion_tokens": raw.get("eval_count", 0),
            "total_tokens": raw.get("prompt_eval_count", 0)
            + raw.get("eval_count", 0),
        }

        return LLMResponse(
            content=content,
            raw=raw,
            usage=usage,
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Generate API (/api/generate)
    # ------------------------------------------------------------------

    async def generate(
        self,
        *,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens or self.default_max_tokens,
            },
        }

        if temperature is not None:
            payload["options"]["temperature"] = temperature

        raw = await self._post("/api/generate", payload)

        content = raw.get("response", "")
        usage = {
            "prompt_tokens": raw.get("prompt_eval_count", 0),
            "completion_tokens": raw.get("eval_count", 0),
            "total_tokens": raw.get("prompt_eval_count", 0)
            + raw.get("eval_count", 0),
        }

        return LLMResponse(
            content=content,
            raw=raw,
            usage=usage,
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Embeddings API (/api/embeddings)
    # ------------------------------------------------------------------

    async def embeddings(
        self,
        *,
        text: str,
        embedding_model: Optional[str] = None,
    ) -> EmbeddingResponse:
        payload = {
            "model": embedding_model or self.model,
            "prompt": text,
        }

        raw = await self._post("/api/embeddings", payload)

        embeddings = raw.get("embedding") or raw.get("embeddings")
        if embeddings is None:
            raise OllamaError("No embeddings returned from Ollama")

        return EmbeddingResponse(
            embeddings=embeddings,
            model=payload["model"],
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Convenience unified interface
    # ------------------------------------------------------------------

    async def invoke(
        self,
        *,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Unified call:
          - messages -> chat
          - prompt   -> generate
        """
        if messages is not None:
            return await self.chat(messages=messages, **kwargs)

        if prompt is not None:
            return await self.generate(prompt=prompt, **kwargs)

        raise ValueError("Either prompt or messages must be provided")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self):
        await self._client.aclose()

