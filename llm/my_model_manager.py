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
#     - Supports optional schema validation
#     - Async-first API
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

# model_manager.py

from typing import Optional, Dict, Any
from llm.ollama_chatmodel import OllamaChatModel  # your custom LLM wrapper
from memory.embedding_factory import EmbeddingFactory
from memory.store_factory import StoreFactory
from memory.memory_manager import MemoryManager
from langgraph.store.memory import InMemoryStore
from langmem.knowledge.extraction import create_memory_store_manager


class ModelManager:
    """
    Production-ready ModelManager integrating:
    - LLMs (Ollama, OpenAI, etc.)
    - MemoryManager (semantic + episodic)
    - EmbeddingFactory
    - StoreFactory (default to InMemoryStore)
    """

    def __init__(
        self,
        model_name: str,
        provider: str = "ollama",
        llm_endpoint: Optional[str] = None,
        stores_config: Optional[Dict[str, Any]] = None,
        embedding_config: Optional[Dict[str, Any]] = None,
        max_tokens: int = 512,
    ):
        # -----------------------
        # 1. Embeddings
        # -----------------------
        self.embedding_factory = EmbeddingFactory(embedding_config or {})
        self.embedding_client = self.embedding_factory.get_embedding()  # default provider

        # -----------------------
        # 2. Stores
        # -----------------------
        self.store_factory = StoreFactory(stores_config or {})
        # Default to InMemoryStore if no stores defined
        self.semantic_store = self.store_factory.get_store("default") or InMemoryStore()
        self.episodic_store = self.store_factory.get_store("default") or InMemoryStore()

        # -----------------------
        # 3. MemoryManager
        # -----------------------
        # Use create_memory_store_manager for helper functionality (vector indexing, etc.)
        self.semantic_store_manager = create_memory_store_manager(
            self.semantic_store,
            model=model_name  # used for vectorization if needed
        )

        self.memory_manager = MemoryManager(
            semantic_store=self.semantic_store_manager,
            episodic_store=self.episodic_store,
            embedding_client=self.embedding_client
        )

        # -----------------------
        # 4️⃣ LLM
        # -----------------------
        self.llm_model_name = model_name
        self.llm_endpoint = llm_endpoint
        self.max_tokens = max_tokens

        if provider.lower() == "ollama":
            self.llm = OllamaChatModel(
                endpoint=llm_endpoint,
                model_name=model_name,
                max_tokens=max_tokens
            )
        else:
            raise NotImplementedError(f"LLM provider {provider} not implemented yet.")

    # -----------------------
    # 5️⃣ Generate Text
    # -----------------------
    async def generate(
        self,
        prompt: str,
        memory_key: Optional[str] = None,
        persist: bool = True,
        embedding_provider: Optional[str] = None
    ) -> str:
        # Persist semantic memory automatically
        if persist and memory_key:
            vector = self.embedding_factory.get_embedding(embedding_provider or None).embed_text(prompt)
            await self.memory_manager.save_semantic(memory_key, prompt, vector)

        # Call LLM
        return await self.llm.ainvoke(prompt)

    # -----------------------
    # 6️⃣ Retrieve Memories
    # -----------------------
    async def retrieve_semantic(
        self,
        query: str,
        top_k: int = 5,
        embedding_provider: Optional[str] = None
    ):
        vector = self.embedding_factory.get_embedding(embedding_provider or None).embed_text(query)
        return await self.memory_manager.retrieve_semantic(query=query, vector=vector, top_k=top_k)
