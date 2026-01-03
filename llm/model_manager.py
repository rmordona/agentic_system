# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/model_manager.py
#
# Description:
#
#   ModelManager orchestrates LLMs and memory for production-grade use:
#     - Handles primary and fallback chat models
#     - Integrates with MemoryManager for semantic and episodic memories
#     - Supports optional schema validation
#     - Supports reward-based persistence, memory decay, summarization
#     - Self-reflection
#     - Async-first API
#
# User/Agent --> ModelManager.generate(prompt)
#    |
#    ├─> MemoryManager.retrieve_semantic()  # fetch context
#    ├─> LLM generates response
#    ├─> MemoryManager.save_semantic()      # save prompt+response, update reward/decay
#    └─> ModelManager._self_reflect()       # optional reflection, saves to episodic store
#
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/model_manager.py
#
# Description:
#
#   ModelManager orchestrates LLMs and memory for production-grade use:
#     - Handles primary and fallback chat models
#     - Integrates with MemoryManager for semantic and episodic memories
#     - Supports reward-based persistence, memory decay, summarization
#     - Self-reflection
#     - Async-first API
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Any
from datetime import datetime

from llm.chatmodels.chatmodel_factory import ChatModelFactory
from llm.embeddings.embedding_factory import EmbeddingFactory
from llm.stores.store_factory import StoreFactory
from llm.memory_manager import MemoryManager
from langgraph.store.memory import InMemoryStore

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

class ModelManager:
    def __init__(
        self,
        chatmodel_provider: str,
        embedding_provider: str,
        episodic_store_provider: str,
        semantic_store_provider: str,
        chatmodels_config: Path,
        embedding_config: Path,
        stores_config: Path,
        max_tokens: int = 512
    ):

        # -----------------------
        # 1. Embeddings
        # -----------------------
        logger.info("Loading Embedding Factory")
        EmbeddingFactory.load_config(embedding_config)
        self.embedding_client = EmbeddingFactory.get(embedding_provider)

        # -----------------------
        # 2. Stores
        # -----------------------
        logger.info("Loading Store Factory")
        StoreFactory.load_config(stores_config)
        self.episodic_store = StoreFactory.get_episodic(episodic_store_provide)
        self.semantic_store = StoreFactory.get_semantic(semantic_store_provide)

        # -----------------------
        # 3. MemoryManager
        # -----------------------
        logger.info("Initializing Memory Manager")
        self.memory_manager = MemoryManager(
            embedding_client = self.embedding,
            episodic_store = self.episodic_store,
            semantic_store = self.semantic_store
        )

        # -----------------------
        # 4. ChatModels
        # -----------------------
        # Load chatmodel config once at platform startup
        logger.info("Loading Chat Model Factory")
        ChatModelFactory.load_config(chatmodels_config)

        # Then in ModelManager
        self.llm = ChatModelFactory.get(
            provider=chatmodel_provider,
            model_name=model_name,
            max_tokens=max_tokens
        )

    # -----------------------
    # Generate Text (Production-Ready)
    # -----------------------
    async def generate(
        self,
        prompt: str,
        memory_key: Optional[str] = None,
        persist: bool = True,
        reward: Optional[float] = None,
        embedding_provider: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """
        Generate text from LLM while automatically:
        - Retrieving relevant semantic memories
        - Prepending context to prompt
        - Persisting new semantic memory (auto-embedding)
        - Reward tracking, decay, summarization
        - Self-reflection (stores reflection in episodic store)
        """

        # 1️⃣ Retrieve relevant semantic memories
        context_memories = []
        if memory_key:
            context_memories = await self.memory_manager.retrieve_semantic(
                query=prompt,
                top_k=top_k,
                metadata_filter=None
            )

        # 2️⃣ Prepend retrieved memories to prompt
        if context_memories:
            context_text = "\n".join([m["text"] for m in context_memories])
            prompt = f"{context_text}\n\n{prompt}"

        # 3️⃣ Call LLM
        response = await self.llm.ainvoke(prompt)

        # 4️⃣ Persist semantic memory (prompt + response)
        if persist and memory_key:
            await self.memory_manager.save_semantic(
                key=memory_key,
                text=f"Prompt: {prompt}\nResponse: {response}",
                metadata={"source": "user_prompt"},
                reward=reward
            )

            # 5️⃣ Self-reflection on saved memory
            await self._self_reflect(key=memory_key, text=f"Prompt: {prompt}\nResponse: {response}")

        return response

    # ----------------------------
    # Self-Reflection (ModelManager)
    # ----------------------------
    async def _self_reflect(self, key: str, text: str):
        """
        Ask LLM to reflect on quality of memory or text.
        Stores reflection in episodic memory.
        """
        if not self.llm:
            return

        reflection_prompt = f"""
Reflect on the quality of the following memory. Suggest improvements or highlights:

{text}
"""
        try:
            # Use the same generate() pipeline but skip memory persistence
            reflection = await self.llm.ainvoke(reflection_prompt)

            # Store in episodic memory for later analysis
            await self.memory_manager.episodic_store.save(
                f"{key}:reflection",
                {
                    "reflection": reflection,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            AgentLogger.warn(f"Self-reflection failed for {key}: {e}")
