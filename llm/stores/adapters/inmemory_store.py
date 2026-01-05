# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/adapters/inmemory_store.py
#
# Description:
#   InMemoryStore is a production-ready, store-agnostic in-memory key/value 
#   storage adapter for episodic memory, user preferences, or other transient
#   data. It optionally supports semantic search using vector embeddings via 
#   an embedding client. Designed to integrate seamlessly with the Agentic 
#   System's MemoryManager and other agents.
#
#   Key Features:
#     - Namespaced key/value storage for multi-user or multi-context usage
#     - Metadata and full-document storage for advanced retrieval
#     - Optional semantic search with vector embeddings (HNSW indexing)
#     - Async-ready API compatible with modern async workflows
#     - Store-agnostic wrapper over LangGraph's InMemoryStore
#
# Usage Examples:
#
#   from llm.stores.adapters.inmemory_store import InMemoryStore
#   from llm.embeddings.adapters.openai_client import OpenAIEmbeddingClient
#
#   # Initialize the store with embeddings for semantic search
#   embeddings = OpenAIEmbeddingClient()
#   store = InMemoryStore(
#       embedding_client=embeddings,
#       dims=1536   # optional depending on embedding model
#   )
#
#   # -------------------------------
#   # Example 1: Save a user preference
#   # -------------------------------
#   store.put(
#       namespace=("user_123", "settings"),
#       key="theme",
#       value="dark",
#       metadata={"updated_by": "system", "timestamp": "2026-01-03T23:45:00Z"}
#   )
#   item = store.get(("user_123", "settings"), "theme")
#   print(item["value"])  # Output: "dark"
#
#   # ---------------------------------------------
#   # Example 2: Save a note and retrieve via semantic search
#   # ---------------------------------------------
#   store.put(
#       namespace=("user_123", "notes"),
#       key="note_001",
#       value="Agentic systems allow autonomous AI agents to execute tasks using memory and reasoning.",
#       metadata={"topic": "ai_systems"}
#   )
#   results = store.search(
#       namespace=("user_123", "notes"),
#       query="Explain autonomous AI agents",
#       limit=3
#   )
#   for r in results:
#       print(r["value"])
#
#   # ---------------------------------------------
#   # Example 3: Delete a key and clear a namespace
#   # ---------------------------------------------
#   store.delete(("user_123", "settings"), "theme")
#   store.clear_namespace(("user_123", "notes"))
#
#   # ---------------------------------------------
#   # Example 4: Use metadata filters in semantic search
#   # ---------------------------------------------
#   results = store.search(
#       namespace=("user_123", "notes"),
#       query="AI agent reasoning",
#       limit=5,
#       metadata_filter={"topic": "ai_systems"}
#   )
#   for r in results:
#       print(r["key"], r["metadata"]["topic"], r["value"])
#
#
#   # ---------------------------------------------------
#   # Example 5: Save a chat message with role
#   # ---------------------------------------------------
#   store.put(
#       namespace=("user_123", "chat_sessions"),
#       key="msg_001",
#       value="Hello! How are you today?",
#       metadata={"role": "user", "timestamp": "2026-01-03T23:50:00Z"}
#   )
#
#   store.put(
#       namespace=("user_123", "chat_sessions"),
#       key="msg_002",
#       value="I'm here to help you with your questions about AI agents.",
#       metadata={"role": "ai", "timestamp": "2026-01-03T23:50:05Z"}
#   )
#
#   # Retrieve a specific message
#   message = store.get(("user_123", "chat_sessions"), "msg_002")
#   print(message["metadata"]["role"], message["value"])
#   # Output: ai I'm here to help you with your questions about AI agents.
#
#   # ---------------------------------------------------
#   # Example 6: Semantic search for relevant chat messages
#   # ---------------------------------------------------
#   results = store.search(
#       namespace=("user_123", "chat_sessions"),
#       query="AI agent help",
#       limit=3,
#       metadata_filter={"role": "ai"}
#   )
#   for r in results:
#       print(r["metadata"]["role"], r["value"])
#
#   # ---------------------------------------------------
#   # Example 7: Clear a chat session
#   # ---------------------------------------------------
#   store.clear_namespace(("user_123", "chat_sessions"))
#
# **************************************************************************
#
# In terms of using metadata to perform metadata_filters.
#
#    store.put(
#        namespace=("user_123", "chat_sessions"),
#        key="msg_001",
#        value={
#            "role": "user",
#            "content": "Hello! How are you today?",
#            "timestamp": "2026-01-03T23:50:00Z"
#       },
#        metadata={"session_id": "sess_001", "topic": "greetings"}
#    )
#
#    store.put(
#        namespace=("user_123", "chat_sessions"),
#        key="msg_002",
#        value={
#            "role": "ai",
#            "content": "I'm here to help you with AI questions.",
#            "timestamp": "2026-01-03T23:50:05Z"
#        },
#        metadata={"session_id": "sess_001", "topic": "ai_help"}
#    )
#
#    store.put(
#        namespace=("user_123", "chat_sessions"),
#        key="msg_003",
#        value={
#            "role": "ai",
#            "content": "Agentic systems can autonomously execute tasks using memory and reasoning.",
#            "timestamp": "2026-01-03T23:51:00Z"
#        },
#        metadata={"session_id": "sess_002", "topic": "ai_systems"}
#    )
#
# Semantic search for AI messages in session "sess_001"
#
#    results = store.search(
#        namespace=("user_123", "chat_sessions"),
#        query="autonomous AI agents",
#        limit=5,
#        metadata_filter={"role": "ai", "session_id": "sess_001"}
#    )
#
# ****************************************************************************************
# In terms of document parameter, the benefits of storing document after LLM generation
#
#        - Reflection & Auditability
#            You can trace why the agent responded a certain way.
#        - Contextual reasoning
#            Agents can retrieve prior LLM outputs to inform next decisions.
#        - Memory augmentation
#            LLM outputs can become enhanced semantic memory entries.
#        - Safe for filtering
#            document can contain large or nested objects without affecting metadata filters or semantic search.
#
# Storing a chat message
#    store.put(
#        namespace=("user_123", "chat_sessions"),
#        key="msg_001",
#        value={"role": "user", "content": "Hello! How are you today?"},
#        metadata={"role": "user", "session_id": "sess_001"},
#        document={
#            "raw_text": "Hello! How are you today?",
#            "intent_detected": "greeting",
#            "entities": [],
#            "conversation_state": {"turn": 1, "context_vector": [0.12, 0.34, 0.56]}
#        }
#    )
# Store AI response with reflection in document
#    store.put(
#        namespace=("user_123", "chat_sessions"),
#        key="msg_002",
#        value={"role": "ai", "content": llm_response},
#        metadata={"role": "ai", "session_id": "sess_001"},
#        document={
#            "reasoning": "Used previous memory of agent types and planning capabilities",
#            "source_notes": ["memory_001", "memory_005"],
#            "timestamp": "2026-01-03T23:50:05Z"
#        }
#    )
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-03
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

import asyncio
from typing import Any, Dict, Optional, Tuple, List
#from llm.stores.adapters.base_store import BaseStore
from langgraph.store.memory import InMemoryStore as LGInMemoryStore
from llm.embeddings.adapters.base_client import BaseEmbeddingClient

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class InMemoryStore:
    """
    LangGraph-backed in-memory store.

    Supports:
    - Namespaced key/value storage
    - Semantic search (embedding handled internally by LangGraph)
    - Metadata filtering
    """

    def __init__(
        self,
        embedding_client: Optional[BaseEmbeddingClient] = None,
        embed: Optional[str] = None,
        dims: Optional[int] = None,
    ):
        self.semantic_enabled = embedding_client is not None

        if self.semantic_enabled:
            self.store = LGInMemoryStore(
                index={
                    "embed": embedding_client.embed_text,
                    "dims": dims,
                }
            )
        elif embed:  # supports this format: openai:text-embedding-3-small
            self.store = LGInMemoryStore(
                index={
                    "embed": embed,
                    "dims": dims,
                }
            )
            self.semantic_enabled = true
        else:
            self.store = LGInMemoryStore()

        logger.info("InMemoryStore initialized")

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    async def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Dict[str, Any],
        semantic: bool = False,
    ):
        logger.info("About to save semantics")
        await self.store.put(namespace, key, value)

    async def get(
        self,
        namespace: Tuple[str, str],
        key: str,
        semantic: bool = False,
    ) -> Optional[Dict[str, Any]]:
        return await self.store.get(namespace, key)

    async def delete(self, namespace: Tuple[str, str], key: str):
        await self.store.delete(namespace, key)

    # ------------------------------------------------------------------
    # Semantic Search
    # ------------------------------------------------------------------
    async def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using LangGraph internal embeddings.
        """

        if not self.semantic_enabled:
            raise RuntimeError("Semantic search not enabled")

        def _search_and_filter():
            results = self.store.search(namespace, query=query, limit=limit)

            # The search internally generates embedding using query, then also does 
            # a similarity search for relevant context
            logger.info(f"Result of similarity search: {results}")

            if metadata_filter:
                results = [
                    r for r in results
                    if all(r.get("metadata", {}).get(k) == v for k, v in metadata_filter.items())
                ]
            return results

        results = await asyncio.to_thread(_search_and_filter)

        logger.info(f"Semantic search for '{query}' returned {len(results)} results")

        return results

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    async def keys(self, namespace: Tuple[str, str]):
        return await self.store.keys(namespace)

    async def clear_namespace(self, namespace: Tuple[str, str]):
        for key in await self.keys(namespace):
            await self.store.delete(namespace, key)

    async def count_namespace(self, namespace: Tuple[str, str]) -> int:
        ns_pattern = f"{self.namespace_prefix}:{namespace[0]}:{namespace[1]}:*"
        keys = await self.redis.keys(ns_pattern)
        return len(keys)
