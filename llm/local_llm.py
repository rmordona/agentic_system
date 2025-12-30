import aiohttp
import asyncio
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import Runnable

MODEL_NAME = "qwen2.5-coder:3b"
ENDPOINT = "http://localhost:11434/api/chat"

class LocalLLM:
    """
    LocalLLM interface for Ollama Docker endpoint using /api/chat.

    Features:
    - Fully async-compatible
    - Supports max token limit
    - Returns assistant text
    - Optional streaming support (False by default)
    """

    def __init__(
        self,
        model_name: str = "qwen2.5-coder:3b",
        endpoint: str = "http://localhost:11434/api/chat",
        timeout: int = 120,
    ):
        """
        Args:
            model_name: Ollama model to use
            endpoint: Ollama Docker API URL
            timeout: request timeout in seconds
        """
        self.model_name = model_name
        self.endpoint = endpoint
        self.timeout = timeout

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate text from the LLM asynchronously.

        Args:
            prompt: user/system input
            max_tokens: max tokens to generate

        Returns:
            Generated assistant text
        """
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(self.endpoint, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(
                        f"Ollama API error {response.status}: {text}"
                    )
                data = await response.json()
                return data.get("message", {}).get("content", "").strip()




class LocalLLMChatModel(BaseChatModel):
    max_tokens: int = 512
    temperature: float = 0.2
    def __init__(self, config: Dict[str, Any]):
        llm_instance = LocalLLM(
                model_name=config.get("model_name", MODEL_NAME),
                endpoint = config.get("endpoint", ENDPOINT)
            )
        max_tokens = config.get("max_tokens", 512)
        temperature = config.get("temperature", 0.2)
        super().__init__(llm=llm_instance, max_tokens=max_tokens, temperature=temperature)

    @property
    def _llm_type(self) -> str:
        return "local-ollama"

    def bind_tools(self, tools, tool_choice=None, **kwargs):
        # Required for LangMem
        return self

    async def _agenerate(
        self,
        messages,
        stop=None,
        **kwargs,
    ) -> ChatResult:
        prompt = self._convert_messages_to_prompt(messages)
        text = await self.llm.generate(
            prompt=prompt,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    def _generate(
        self,
        messages,
        stop=None,
        **kwargs,
    ) -> ChatResult:
        """
        REQUIRED sync fallback.
        LangChain still calls this in some paths.
        """
        return asyncio.run(self._agenerate(messages, stop=stop, **kwargs))



    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """
        Convert LangChain chat messages into a single prompt string
        suitable for Ollama /api/chat.
        """
        parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                parts.append(f"[SYSTEM]\n{msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(f"[USER]\n{msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"[ASSISTANT]\n{msg.content}")
            else:
                parts.append(f"[MESSAGE]\n{msg.content}")
        return "\n\n".join(parts)
