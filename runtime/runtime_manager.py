# workspace_session_manager.py

from __future__ import annotations
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional, Any

from runtime.workspace_loader import WorkspaceLoader
from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
from runtime.graph_manager import GraphManager
from runtime.reload_manager import ReloadManager
from runtime.orchestrator import Orchestrator
from runtime.session_manager import SessionManager
from runtime.lifecycle import register_lifecycle_handlers
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient

from events.event_bus import EventBus

from runtime.logger import AgentLogger
# Initialization of logger is done at cli.py or api.py



class RuntimeManager:
    """
    Singleton per workspace.
    - Holds singleton registries and graph manager.
    - Manages per-session orchestrators.
    - Supports multi-session execution safely.
    """

    # Inherit the logger
    #llm_manager = None
    #memory_manager = None
    #embedding_store = None
    tool_client = None
    event_bus = None

    _instances: Dict[str, RuntimeManager] = {}

    def __new__(cls, 
            workspace_path: Path,
            model_manager: ModelManager,
            session_manager: SessionManager,
            #memory_manager: MemoryManager, 
            #embedding_store: EmbeddingStore, 
            tool_client: ToolClient,
            event_bus: EventBus,
        ):
        ws_name = workspace_path.name
        if ws_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[ws_name] = instance
        return cls._instances[ws_name]

    def __init__(self, 
            workspace_path: Path,
            model_manager: ModelManager,
            session_manager: SessionManager,
            #memory_manager: MemoryManager, 
            #embedding_store: EmbeddingStore, 
            tool_client: ToolClient,
            event_bus: EventBus,
        ):

        if hasattr(self, "_initialized") and self._initialized:
            return  # Avoid re-initialization

        self._initialized = True

        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.model_manager = model_manager
        # self.memory_manager = memory_manager
        #self.embedding_store = embedding_store
        self.tool_client = tool_client

        self.event_bus = event_bus

        # 🔑 Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(component="runtime", workspace=self.workspace_name)

        # ---- Singletons (loaded once per workspace) ----
        # Load Workspace Configuration (workspace.json)
        self.workspace_meta = WorkspaceLoader(workspace_path).load_workspace()
        logger.info(f"Workspace metadata loaded: {self.workspace_meta.get('name')}")

        self.agent_registry = AgentRegistry(
            workspace_path,
            model_manager=self.model_manager,
            #memory_manager=self.memory_manager,
            #embedding_store=self.embedding_store,
            tool_client=self.tool_client,
            event_bus=self.event_bus
        )
        self.agent_registry.load_agents()
        logger.info(f"Registered agents: {self.agent_registry.roles()}")

        self.stage_registry = StageRegistry(workspace_path)
        self.stage_registry.load_stages()
        logger.info(f"Stages loaded: {self.stage_registry.list_stages()}")

        self.graph_manager = GraphManager(workspace_path, self.agent_registry, self.stage_registry)
        self.graph_manager.build()
        logger.info("Execution graph built successfully")

        self.reload_manager = ReloadManager(
            workspace_loaders={self.workspace_name: self.workspace_meta},
            graph_manager=self.graph_manager,
            interval_seconds=30
        )
                        
        self.reload_manager.start_periodic_reload()
        logger.info("Hot-reload enabled for skills/context")

        #self.event_bus = EventBus()
       # logger.info("Event Bus loaded")

        # ---- Per-session storage ----
        self._orchestrators: Dict[str, Orchestrator] = {}

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new session with a fresh orchestrator.
        Returns the session_id.
        """
        session_id = session_id or str(uuid.uuid4())

        # Stage registry, event bus, orchestrator
        register_lifecycle_handlers(self.event_bus)

        orchestrator = Orchestrator(
            workspace_path=self.workspace_path,
            agent_registry=self.agent_registry,
            stage_registry=self.stage_registry,
            graph_manager=self.graph_manager,
            event_bus=self.event_bus,
            session_id=session_id
        )
        self._orchestrators[session_id] = orchestrator
        logger.info(f"Created new session: {session_id}")
        return session_id

    def get_orchestrator(self, session_id: str) -> Orchestrator:
        """
        Retrieve orchestrator for a session.
        """
        orchestrator = self._orchestrators.get(session_id)
        if not orchestrator:
            logger.error(f"No orchestrator found for session {session_id}")
            raise ValueError(f"No orchestrator found for session {session_id}")
        return orchestrator

    async def run_user_message(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry for CLI or API:
        - Injects user message into session state
        - Runs orchestrator
        """
        # 1. Create or fetch session
        if session_id and session_id in self._orchestrators:
            orchestrator = self.get_orchestrator(session_id)
        else:
            session_id = self.create_session(session_id)
            orchestrator = self.get_orchestrator(session_id)

        # 2. Initialize session state with user message
        initial_state = {
            "session_id": session_id,
            "task": user_message,
            "stage": self.stage_registry.first_stage(),
            "done": False,
            "history_agents": [],
            "executed_agents_per_stage": {},
            "rewards": {},
            "winner": {},
            "decision": {},
        }

        if verbose:
            logger.info(f"Running session {session_id} with user message: {user_message}")


        # 3. Run orchestrator
        result = await orchestrator.run(initial_state)
        return result

    # ------------------------------------------------------------------
    # Session Utilities
    # ------------------------------------------------------------------

    def list_sessions(self) -> list[str]:
        return list(self._orchestrators.keys())

    def close_session(self, session_id: str):
        if session_id in self._orchestrators:
            del self._orchestrators[session_id]
            logger.info(f"Closed session {session_id}")

    def close_all_sessions(self):
        self._orchestrators.clear()
        logger.info("Closed all sessions")

