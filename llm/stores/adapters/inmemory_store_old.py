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

import numpy as np
from typing import Any, Dict, Optional, Tuple, List
from llm.stores.adapters.base_store import BaseStore
from langgraph.store.memory import InMemoryStore as LGInMemoryStore
from llm.embeddings.adapters.base_client import BaseEmbeddingClient

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class InMemoryStore(BaseStore):
    """
    Production-ready in-memory store supporting:
      1. Key/value storage for raw episodic memory
      2. Metadata and document storage
      3. Optional semantic search using vector embeddings
    """

    def __init__(
        self,
        index: Optional[Dict[str, Any]] = None,  # Expect that control of index is done externally
        embedding_client: Optional[BaseEmbeddingClient] = None,
        embed: Optional[str] = None,
        dims: Option[int] = None
    ):
        """
        Args:
            index: dict with "embed", "dims", "fields" keys to initialize HNSW index
            embedding_client: instance of BaseEmbeddingClient to vectorize text for semantic search
        """

        logger.info(f"Lazy registering this adapter based on user preference: {__name__}")

        self.store = LGInMemoryStore()
        self.embedding_client = embedding_client
        self.embed = embed
        self.semantic_index_enabled = False

        logger.info(f"Embedding client provided: {embedding_client}")

        if embedding_client:
            # Enable semantic search mode
            self.store = LGInMemoryStore(index={
                "embed" : self.embedding_client,
                "dims" : dims
            })
            self.semantic_index_enabled = True
        elif embed:
            self.store = LGInMemoryStore(index={
                "embed" : self.embed,
                "dims" : dims
            })


    # --------------------------
    # Key/Value + Metadata + Document Operations
    # --------------------------
    def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None
    ):
        """
        Store a value under a namespaced key, with optional metadata and full document.

        Args:
            namespace: tuple like ("user_123", "settings") or ("user_123", "memories")
            key: unique key under namespace
            value: main value (text or object)
            metadata: optional structured data for filtering
            document: optional full object for retrieval, logging, or reflection
        """
        item = {
            "value": value,
            "metadata": metadata or {},
            "document": document or {}
        }

        if self.semantic_index_enabled and self.embedding_client:
            # Compute embedding vector for semantic search
            item["vector"] = self.embedding_client.embed_text(value)

        self.store.put(namespace, key, item)

    def get(self, namespace: Tuple[str, str], key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a stored value, including metadata and document
        """
        return self.store.get(namespace, key)

    def delete(self, namespace: Tuple[str, str], key: str):
        """
        Delete a stored value by key
        """
        self.store.delete(namespace, key)

    # --------------------------
    # Semantic Search
    # --------------------------
    def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on stored objects.

        Args:
            namespace: tuple defining the namespace
            query: natural language query string
            limit: maximum number of results
            metadata_filter: optional dict to filter items by metadata

        Returns:
            List of items with 'key', 'value', 'metadata', 'document', 'score' (cosine similarity)
        """
        if not self.semantic_index_enabled or not self.embedding_client:
            raise RuntimeError("Semantic search not enabled. Provide embeddings and initialize index.")

        logger.info("Running embed_text ...")
        query_vector = self.embedding_client.embed_text(query)

        vector_dim = len(query_vector)

        logger.info(f"Received Vector -> Length of Dimension: {vector_dim}")

        # Perform similarity search using HNSW / cosine similarity
        results = self.store.search(namespace=namespace, query=query_vector, limit=limit)

        # Optional metadata filtering
        if metadata_filter:
            def matches_metadata(item):
                return all(item["metadata"].get(k) == v for k, v in metadata_filter.items())
            results = [r for r in results if matches_metadata(r)]

        return results

    # --------------------------
    # Utility Methods
    # --------------------------
    def clear_namespace(self, namespace: Tuple[str, str]):
        """
        Clears all keys under a namespace
        """
        keys = list(self.store.keys(namespace))
        for key in keys:
            self.store.delete(namespace, key)

    def count_namespace(self, namespace: Tuple[str, str]) -> int:
        """
        Count the number of entries under a namespace
        """
        return len(list(self.store.keys(namespace)))
