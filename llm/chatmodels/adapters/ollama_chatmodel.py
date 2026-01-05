# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/chatmodels/adapters/ollama_chatmodel.py
#
# Description:
#   OllamaChatModel is a production-grade LangChain-compatible chat model
#   adapter for interacting with Ollama-hosted large language models.
#   It implements the BaseChatModel interface and is designed for use
#   within provider-driven factories and configuration-based systems.
#
#   The adapter supports synchronous generation, synchronous streaming,
#   and asynchronous streaming, enabling seamless integration into both
#   blocking and non-blocking agent workflows.
#
#   This class is intended to be instantiated declaratively via configuration
#   and factory mechanisms rather than manual attribute mutation. Configuration
#   values are supplied at construction time and validated as part of the
#   model’s lifecycle, consistent with LangChain and Pydantic design patterns.
#
# Key Features:
#   - LangChain BaseChatModel compatibility
#   - Provider-agnostic factory integration
#   - Config-driven initialization
#   - Sync, streaming, and async streaming support
#   - Production-safe request handling with configurable timeouts
#   - Structured message conversion for Ollama chat APIs
#
# Usage:
#   1. Define the Ollama provider in a chat model configuration file.
#   2. Resolve the provider via ChatModelFactory or equivalent factory.
#   3. Instantiate the model declaratively by passing configuration fields.
#   4. Use the resulting instance via LangChain’s invoke(), stream(),
#      or astream() interfaces.
#
# Example:
#   llm = ChatModelFactory.get(
#       provider="ollama",
#       model_name="llama3"
#   )
#
#   response = llm.invoke("Explain agentic systems in one paragraph.")
#
# Notes:
#   - This adapter follows LangChain’s declarative model instantiation
#     pattern and should not rely on imperative attribute assignment
#     after construction.
#   - Validation and compatibility checks are expected to occur at
#     initialization time or within the factory layer.
#   - The adapter is suitable for local development and production
#     deployments where Ollama is available as an inference backend.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-02
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations

from typing import Iterator, AsyncIterator, List, Optional, Dict, Any
import json
import requests
import httpx

from pydantic import Field, ConfigDict

from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs.chat_result import (
    ChatGeneration,
    ChatResult,
)

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class OllamaChatModel(BaseChatModel):
    """
    Production-grade LangChain chat adapter for Ollama.

    ✔ Pydantic-safe
    ✔ Factory-safe
    ✔ Streaming + async streaming
    ✔ Config-driven
    """

    # ------------------------------------------------------------------
    # Pydantic / LangChain configuration
    # ------------------------------------------------------------------
    model_config = ConfigDict(
        extra="ignore",          # ignore unknown kwargs from factories
        arbitrary_types_allowed=True,
    )

    # ------------------------------------------------------------------
    # Declared fields (REQUIRED for BaseChatModel)
    # ------------------------------------------------------------------
    model_name: str = Field(
        ...,
        description="Ollama model name (e.g. llama3, mistral)",
    )

    endpoint: str = Field(
        default="http://localhost:11434/api/chat",
        description="Ollama chat endpoint",
    )

    max_tokens: int = Field(
        default=512,
        ge=1,
        description="Maximum tokens to generate",
    )

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )

    request_timeout: float = Field(
        default=120.0,
        ge=1.0,
        description="HTTP request timeout in seconds",
    )

    models: Optional[List[str]] = Field(
        default=None,
        description="Optional allowlist of supported model names",
    )

    apis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional API configuration (reserved)",
    )

    # ------------------------------------------------------------------
    # Post-init validation (SAFE with Pydantic)
    # ------------------------------------------------------------------

    def model_post_init(self, __context: Any) -> None:
        if not self.model_name:
            logger.error("model_name must be provided")
            raise ValueError("model_name must be provided")

        if self.models and self.model_name not in self.models:
            logger.error(
                "Model '%s' not in supported list: %s",
                self.model_name,
                self.models,
            )
            raise ValueError(
                f"Model '{self.model_name}' is not in supported list {self.models}"
            )

        logger.info(
            "OllamaChatModel initialized | model=%s endpoint=%s",
            self.model_name,
            self.endpoint,
        )

    # ------------------------------------------------------------------
    # REQUIRED by BaseChatModel
    # ------------------------------------------------------------------

    @property
    def _llm_type(self) -> str:
        return "ollama"

    # ------------------------------------------------------------------
    # NON-STREAMING
    # ------------------------------------------------------------------

    def _generate(
        self,
        messages: List[HumanMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> ChatResult:
        payload = self._build_chat_payload(messages, stream=False)

        logger.info(f"Building the payload ... {payload}")
        response = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.request_timeout,
        )

        logger.info(f"LLM Reponse status: {response}")
        response.raise_for_status()

        data = response.json()

        logger.info(f"Raw Data: {data}")
        content = data.get("message", {}).get("content", "")

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=content)
                )
            ]
        )

    # ------------------------------------------------------------------
    # STREAMING (sync)
    # ------------------------------------------------------------------

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> Iterator[ChatGeneration]:
        payload = self._build_chat_payload(messages, stream=True)

        with requests.post(
            self.endpoint,
            json=payload,
            stream=True,
            timeout=self.request_timeout,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                data = self._parse_stream_chunk(line)
                token = data.get("message", {}).get("content")

                if token:
                    yield ChatGeneration(
                        message=AIMessage(content=token)
                    )

    # ------------------------------------------------------------------
    # STREAMING (async)
    # ------------------------------------------------------------------

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> AsyncIterator[ChatGeneration]:
        payload = self._build_chat_payload(messages, stream=True)

        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            async with client.stream(
                "POST",
                self.endpoint,
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    data = self._parse_stream_chunk(line)
                    token = data.get("message", {}).get("content")

                    if token:
                        yield ChatGeneration(
                            message=AIMessage(content=token)
                        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_chat_payload(
        self,
        messages: List[BaseMessage],
        *,
        stream: bool,
    ) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "stream": stream,
            "messages": [self._convert_message(m) for m in messages],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

    def _convert_message(self, message: BaseMessage) -> Dict[str, str]:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")

        return {
            "role": role,
            "content": message.content,
        }

    def _parse_stream_chunk(self, raw_line: bytes | str) -> Dict[str, Any]:
        if isinstance(raw_line, bytes):
            raw_line = raw_line.decode("utf-8")

        try:
            return json.loads(raw_line)
        except json.JSONDecodeError:
            return {}
