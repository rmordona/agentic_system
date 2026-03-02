# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/platform_runtime.py
#
# Description:
#   Initializes and orchestrates the Agentic platform, including configuration
#   loading, LLM and chat model setup, embedding and store factories, and
#   the MemoryManager, enabling seamless integration of semantic and episodic
#   memories, LLM orchestration, and self-reflection.
#
# Author: Raymond M.O. Ordona
# Created: 2025-12-31
# Copyright:
#   © 2025 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------
#                        ┌────────────────────────────┐
#                        │      Platform Startup      │
#                        │ (reads JSON configs)       │
#                        └─────────────┬──────────────┘
#                                      │
#            ┌─────────────────────────┴─────────────────────────┐
#            │                                                   │
#            ▼                                                   ▼
#┌─────────────────────────────┐                       ┌─────────────────────────────┐
#│ embeddings/config.json      │                       │ stores/config.json          │
#│ - Default provider          │                       │ - Default store             │
#│ - OpenAI, Cohere, Ollama    │                       │ - InMemory, Redis, Chroma   │
#│                             │                       │ - Oracle, Postgres          │
#└─────────────┬───────────────┘                       └─────────────┬───────────────┘
#              │                                                   │
#              ▼                                                   ▼
#   ┌─────────────────────┐                               ┌──────────────────────┐
#   │ EmbeddingFactory    │                               │ StoreFactory         │
#   │ - Standard .embed() │                               │ - Provides stores    │
#   │ - Returns BaseEmbed │                               │   (semantic/episodic)│
#   └─────────┬───────────┘                               └─────────┬────────────┘
#             │                                                     │
#             ▼                                                     ▼
#       ┌─────────────────────────────────────────────────────────────┐
#       │                  MemoryManager                              │
#       │ - Receives stores & embedding client                        │
#       │ - CRUD operations: save/retrieve semantic & episodic        │
#       │ - Auto embedding, reward tracking, decay, summarization     │
#       │ - **No self-reflection here**                               │
#       └───────────────┬─────────────────────────────┬───────────────┘
#                       │                             │
#                       ▼                             ▼
#      Semantic Store (vectorized)           Episodic Store (raw logs)
#      e.g., Redis, Chroma, Postgres         e.g., Redis, Postgres, In-Memory (fallback)
#
#
#           chatmodels/config.json
#           - Ollama, OpenAI, Cohere, etc.
#           - API endpoints, payload templates
#                       │
#                       ▼
#               ChatModelFactory
#               - Returns LLM instances (OllamaChatModel, OpenAIChatModel, etc.)
#                       │
#                       ▼
#                 ModelManager
#                 - Orchestrates LLM + MemoryManager
#                 - Handles:
#                   • generate(prompt)
#                     - Fetch top-K semantic memory
#                     - Prepend context
#                     - Call LLM
#                     - Save semantic memory
#                     - Self-reflection (episodic store)
#
# -----------------------------------------------------------------------------
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from runtime.logger import AgentLogger
from runtime.bootstrap.config_loader import ConfigLoader
from runtime.bootstrap.workspace_hub import WorkspaceHub
from runtime.bootstrap.session_manager import SessionManager

from events.event_bus import EventBus


class Platform:
    """
    Process-wide singleton runtime for the agentic platform.
    Provides access to memory, embedding store, tool client, and logging.
    """
    session_manager: SessionManager | None = None
    workspace_hub: WorkspaceHub | None = None
    event_bus: EventBus | None = None
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        # --------------------------------------------------
        # Config
        # --------------------------------------------------
        cls.config = ConfigLoader().load()

        # --------------------------------------------------
        # Initialize Logger
        # -------------------------------------------------
        AgentLogger.initialize()

        logger = AgentLogger.get_logger(component="system")

        logger.info("Bootstrapping this Agentic Platform")

        # --------------------------------------------------
        # Event Bus
        # --------------------------------------------------
        cls.event_bus = EventBus()

        # --------------------------------------------------
        # Session Bootstrapping
        # --------------------------------------------------
        cls.session_manager = SessionManager()

        # --------------------------------------------------
        # Workspace Hub
        # --------------------------------------------------
        cls.workspace_hub = WorkspaceHub(
            session_manager=cls.session_manager,
            event_bus=cls.event_bus
        )


        cls._initialized = True
        logger.info("PlatformRuntime initialized successfully")
