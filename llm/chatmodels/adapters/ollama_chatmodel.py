# ollama_adapter.py


from typing import Iterator, AsyncIterator, List, Optional
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

class OllamaChatModel(BaseChatModel):
    """Production-grade Ollama chat adapter"""

    model_name: str
    endpoint: str
    max_tokens: int = 512
    temperature: float = 0.7

    # ------------------------------------------------------------------
    # REQUIRED by BaseChatModel
    # ------------------------------------------------------------------

    @property
    def _llm_type(self) -> str:
        return "ollama"

    # ------------------------------------------------------------------
    # NON-STREAMING (required)
    # ------------------------------------------------------------------

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
    ) -> ChatResult:
        """
        Called when streaming=False
        """
        payload = self._build_chat_payload(messages, stream=False)
        response = requests.post(self.endpoint, json=payload, timeout=120)
        response.raise_for_status()

        content = response.json()["message"]["content"]

        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=content))
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
        """
        Called when streaming=True (sync)
        """
        payload = self._build_chat_payload(messages, stream=True)

        with requests.post(
            self.endpoint,
            json=payload,
            stream=True,
            timeout=120,
        ) as r:
            r.raise_for_status()

            for line in r.iter_lines():
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
        """
        Called when streaming=True (async)
        """
        payload = self._build_chat_payload(messages, stream=True)

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                self.endpoint,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    data = self._parse_stream_chunk(line)
                    token = data.get("message", {}).get("content")

                    if token:
                        yield ChatGeneration(
                            message=AIMessage(content=token)
                        )

