from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from llm.local_llm import LocalLLMChatModel
from runtime.config_loader import ConfigLoader
from runtime.logger import AgentLogger
from runtime.workspace_hub import WorkspaceHub
from runtime.session_manager import SessionManager

# Memory
from runtime.memory_manager import MemoryManager
from runtime.embeddings.base import EmbeddingStore
from runtime.memory_adapters.memory_factory import MemoryFactory
from runtime.embeddings.embedding_factory import EmbeddingFactory 


# Tools
from runtime.tools.registry import ToolRegistry
from runtime.tools.policy import ToolPolicy
from runtime.tools.client import ToolClient

from events.event_bus import EventBus


class PlatformRuntime:
    """
    Process-wide singleton runtime for the agentic platform.
    Provides access to memory, embedding store, tool client, and logging.
    """

    _initialized = False

    session_manager: SessionManager = None
    memory_manager: MemoryManager = None
    embedding_store: EmbeddingStore = None
    tool_registry: ToolRegistry = None
    tool_policy: ToolPOlicy = None
    tool_client: ToolClient = None
    workspace_hub: WorkspaceHub = None
    event_bus: EventBus = None


    logger = None

    @classmethod
    def initialize(
        cls,
        *,
        workspaces_root: Path,
    ):
        if cls._initialized:
            return

        # --------------------------------------------------
        # Config
        # --------------------------------------------------
        parent_path = Path(__file__).parent
        config_path = parent_path / "config.json"  # runtime/config.json
        config_loader = ConfigLoader(global_config_path=config_path, workspaces_root=workspaces_root)
        cls.config = config_loader.load()

        # --------------------------------------------------
        # Tools Config
        # --------------------------------------------------
        tool_config_path = parent_path / "tools" / "config.json" # runtime/tools/config.json
        tools_policy_path = workspaces_root / "tools_policy.json" # workspaces/tools_config.json

        # --------------------------------------------------
        # Logging
        # --------------------------------------------------
        AgentLogger.initialize(
            log_dir=Path(cls.config["logging"]["base_dir"]),
            log_level=cls.config["logging"]["level"]
        )
        cls.logger = AgentLogger.get_logger(
            workspace=None,
            component="system",
        )

        logger = cls.logger

        logger.info("Initializing PlatformRuntime")

        # --------------------------------------------------
        # Event Bus
        # --------------------------------------------------
        cls.event_bus = EventBus()

        # --------------------------------------------------
        # LLM bootstrapping
        # --------------------------------------------------
        llm_config = cls.config["llm"]["model"]
        cls.llm = LocalLLMChatModel(
            config=llm_config
        )

        # --------------------------------------------------
        # Embedding store
        # --------------------------------------------------
        embedding_config = cls.config.get("embeddings", {})
        cls.embedding_store = EmbeddingFactory.build(config=embedding_config, logger=cls.logger)


        # --------------------------------------------------
        # Tool Bootstrapping
        # --------------------------------------------------
    
        cls.tool_registry = ToolRegistry(tool_config_path)
        cls.tool_registry.load()

        cls.tool_policy = ToolPolicy(
            json.loads(tools_policy_path.read_text())
        )

        cls.tool_client = ToolClient(
            registry=cls.tool_registry,
            policy=cls.tool_policy,
            agent_role="critic"
        )
        logger.info("ToolClient initialized")

        # --------------------------------------------------
        # Session Bootstrapping
        # --------------------------------------------------
        cls.session_manager = SessionManager()

        # --------------------------------------------------
        # Memory Manager
        # --------------------------------------------------
        episodic_adapter = MemoryFactory.build(
            cls.config["memory"]["episodic"]
        )
        semantic_adapter = MemoryFactory.build(
            cls.config["memory"]["semantic"],
            llm=cls.llm,
            embedding_store=cls.embedding_store,
        )

        cls.memory_manager = MemoryManager(
            episodic=episodic_adapter,
            semantic=semantic_adapter
        )


        # --------------------------------------------------
        # Workspace Hub
        # --------------------------------------------------
        cls.workspace_hub = WorkspaceHub(
            workspaces_root=workspaces_root,
            llm=cls.llm,
            session_manager=cls.session_manager,
            memory_manager=cls.memory_manager,
            embedding_store=cls.embedding_store,
            tool_client=cls.tool_client,
            event_bus=cls.event_bus
        )

        cls._initialized = True
        logger.info("PlatformRuntime initialized successfully")
