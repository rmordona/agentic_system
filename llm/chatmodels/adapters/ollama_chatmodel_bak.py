# ollama_adapter.py

from __future__ import annotations

from typing import Iterator, AsyncIterator, List, Optional, Dict, Any
import json
import requests
import httpx

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

logger = AgentLogger.get_logger(  component="system")

class OllamaChatModel(BaseChatModel):
    def __init__(
        self,
        model_name: str = None,
        models: Optional[List[str]] = None,
        endpoint: Optional[str] = None,
        max_tokens: Optional[int] = 512,
        temperature: Optional[float] = 0.7,
        request_timeout: Optional[float] = 120.0,
        apis: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the Ollama chat model.

        Args:
            model_name: Ollama model name (e.g. "llama3", "mistral")
            endpoint: Ollama chat endpoint
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            request_timeout: HTTP timeout in seconds
        """

        logger.info(f"Here now it is ... {model_name}")
        if not model_name:
                log.error("Model Name must be provided for Generation of embeddings.")
                raise ValueError("Model Name must be provided for Generation of embeddings.")

        if models and model_name not in models:
                log.error(f"Model Name {model_name} is not in the supported list {models}.")
                raise ValueError(f"Model Name {model_name} is not in the supported list {models}.")  

        logger.info("ok now 1")
        self.model_name = model_name
        logger.info("ok now 2")
        self.endpoint = endpoint
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.request_timeout = request_timeout

        logger.info(f"Adapter '{__name__}' initialized ...")

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
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
    ) -> ChatResult:
        payload = self._build_chat_payload(messages, stream=False)

        response = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        data = response.json()
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
        """
        Convert LangChain messages into Ollama chat format.
        """
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
        """
        Convert LangChain message to Ollama role/content format.
        """
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
        """
        Parse a single Ollama streaming JSON chunk.
        """
        if isinstance(raw_line, bytes):
            raw_line = raw_line.decode("utf-8")

        try:
            return json.loads(raw_line)
        except json.JSONDecodeError:
            return {}
