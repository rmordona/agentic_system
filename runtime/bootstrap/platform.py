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
from runtime.workspace_hub import WorkspaceHub
from runtime.session_manager import SessionManager

# LLM Model Manager
from llm.model_manager import ModelManager

# Tools
from runtime.tools.tool_registry import ToolRegistry
from runtime.tools.tool_policy import ToolPolicy
from runtime.tools.tool_client import ToolClient

from events.event_bus import EventBus


class Platform:
    """
    Process-wide singleton runtime for the agentic platform.
    Provides access to memory, embedding store, tool client, and logging.
    """

    _initialized = False

    model_manager: ModelManager = None
    session_manager: SessionManager = None
    tool_registry: ToolRegistry = None
    tool_policy: ToolPOlicy = None
    tool_client: ToolClient = None
    workspace_hub: WorkspaceHub = None
    event_bus: EventBus = None




    @classmethod
    def initialize(
        self,
        *,
        workspaces_root: Path,
    ):
        if self._initialized:
            return

        # --------------------------------------------------
        # Config
        # --------------------------------------------------
        parent_path = Path(__file__).parent
        config_path = parent_path / "config.json"  # runtime/config.json

        config_loader = ConfigLoader(global_config_path=config_path, workspaces_root=workspaces_root)
        self.config = config_loader.load()


        # --------------------------------------------------
        # Initialize Logger
        # -------------------------------------------------
        AgentLogger.initialize()

        logger = AgentLogger.get_logger(component="system")

        logger.info("Bootstrapping this Agentic Platform")

        # --------------------------------------------------
        # Tools Config
        # --------------------------------------------------
        tool_config_path = parent_path.parent / "tools" / "config.json" # runtime/tools/config.json
        tools_policy_path = workspaces_root / "tools_policy.json" # workspaces/tools_config.json

        # --------------------------------------------------
        # Tool Bootstrapping
        # --------------------------------------------------
    
        self.tool_registry = ToolRegistry(tool_config_path)
        self.tool_registry.load()

        self.tool_policy = ToolPolicy(
            json.loads(tools_policy_path.read_text())
        )

        self.tool_client = ToolClient(
            registry=self.tool_registry,
            policy=self.tool_policy,
            agent_role="critic"
        )
        logger.info("ToolClient initialized")

        # --------------------------------------------------
        # Event Bus
        # --------------------------------------------------
        self.event_bus = EventBus()
        # --------------------------------------------------
        # LLM Model bootstrap
        # --------------------------------------------------

        # Load configs
        llm_config = parent_path.parent.parent / "llm"
        embedding_config  = llm_config / "embeddings/config.json"
        stores_config     = llm_config / "stores/config.json"
        chatmodels_config = llm_config / "chatmodels/config.json"

        # Initialize ModelManager
        # user preference
        model_manager = ModelManager(
            chatmodel_provider="ollama",
            embedding_provider="ollama",
            episodic_store_provider="in-memory", # or redis
            semantic_store_provider="postgres", #pgvector
            chatmodels_config=chatmodels_config,
            embedding_config=embedding_config,
            stores_config=stores_config,
            max_tokens=1024
        )


        # --------------------------------------------------
        # Embedding store
        # --------------------------------------------------
        #embedding_config = self.config.get("embeddings", {})
        #self.embedding_store = EmbeddingFactory.build(config=embedding_config, logger=self.logger)

        # --------------------------------------------------
        # Session Bootstrapping
        # --------------------------------------------------
        self.session_manager = SessionManager()

        # --------------------------------------------------
        # Memory Manager
        # --------------------------------------------------
        '''
        episodic_adapter = MemoryFactory.get_episodic_adapter(
            cls.config["memory"]["episodic"]
        )
        semantic_adapter = MemoryFactory.get_semantic_adapter(
            cls.config["memory"]["semantic"],
            llm_manager=cls.llm_manager,
            embedding_store=cls.embedding_store,
        )
 
        episodic_adapter = None
        semantic_adapter = None
        '''



        # --------------------------------------------------
        # Workspace Hub
        # --------------------------------------------------
        self.workspace_hub = WorkspaceHub(
            workspaces_root=workspaces_root,
            model_manager=self.model_manager,
            session_manager=self.session_manager,
            #memory_manager=self.memory_manager,
            #embedding_store=self.embedding_store,
            tool_client=self.tool_client,
            event_bus=self.event_bus
        )

        self._initialized = True
        logger.info("PlatformRuntime initialized successfully")
