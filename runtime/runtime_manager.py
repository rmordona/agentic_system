# workspace_session_manager.py

from __future__ import annotations
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional, Any


from runtime.workspace_loader import WorkspaceLoader
from runtime.core_engine import CoreEngine
from runtime.runtime_context import RuntimeContext
from runtime.reload_manager import ReloadManager
from runtime.orchestrator import Orchestrator
from runtime.session_manager import SessionManager, SessionContext
from runtime.lifecycle import register_lifecycle_handlers

from events.event_bus import EventBus

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger( component="system" )

class RuntimeManager:
    """
    Singleton per workspace.
    - Holds singleton registries and graph manager.
    - Manages per-session orchestrators.
    - Supports multi-session execution safely.
    """

    event_bus = None

    _instances: Dict[str, RuntimeManager] = {}

    def __new__(cls, 
            workspace_path: Path,
            session_manager: SessionManager,
            event_bus: EventBus,
        ):
        ws_name = workspace_path.name
        if ws_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[ws_name] = instance
        return cls._instances[ws_name]

    def __init__(self, 
            workspace_path: Path,
            session_manager: SessionManager,
            event_bus: EventBus,
        ):

        if hasattr(self, "_initialized") and self._initialized:
            return  # Avoid re-initialization

        self._initialized = True

        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.runtime_path = workspace_path.parent

        self.session_manager = session_manager



        #self.model_manager = model_manager
        #self.tool_client = tool_client

        self.event_bus = event_bus

        #global logger
        #logger = AgentLogger.get_logger( component="runtime", workspace = self.workspace_name )


        logger.info(f"Initializaing Runtime {self.workspace_name}... ")

        # ---- Singletons (loaded once per workspace) ----
        # Load Workspace Configuration (workspace.json)
        self.workspace_meta = WorkspaceLoader(workspace_path).load_workspace()
        logger.info(f"Workspace metadata loaded: {self.workspace_meta.get('name')}")

        self.execution_mode = self.workspace_meta.get('execution_mode')
        logger.info(f"Workspace Execution Mode: {self.execution_mode}")


        self.reload_manager = ReloadManager(
            workspace_loaders={self.workspace_name: self.workspace_meta},
            interval_seconds=30
        )
                        
        self.reload_manager.start_periodic_reload()
        logger.info("Hot-reload enabled for skills/context")


        # ---- Per-session storage ----
        self._orchestrators: Dict[str, Orchestrator] = {}

    def get_orchestrator(self, session_ctx: SessionContext) -> Orchestrator:
        """
        Retrieve orchestrator for a session.
        """

        if session_ctx.session_id in self._orchestrators:
            logger.info(f"Acquiring orchestrator for session: {session_ctx.session_id}")
            orchestrator = self._orchestrators.get(session_ctx.session_id)
        else:
            logger.info(f"Creating new orchestrator for session: {session_ctx.session_id}")
            orchestrator = Orchestrator(
                workspace_path=self.workspace_path,
                session_id=session_ctx.session_id,
                event_bus=self.event_bus
            )
            self._orchestrators[session_ctx.session_id] = orchestrator
        return orchestrator

    async def run_user_message(
        self,
        user_id: str,
        user_intent: str,
        session_id: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry for CLI or API:
        - Injects user message into session state
        - Runs orchestrator
        """

        logger.info("Entering Session Space")

        # 1. Create or fetch session
        if session_id and self.session_manager.exists(user_id, session_id):
            session_ctx = self.session_manager.get(session_id)
        else:
            session_ctx = self.session_manager.create_session(user_id)

        orchestrator = self.get_orchestrator(session_ctx)

        logger.info(f"Running session {session_id} with user message: {user_intent}")

 
        logger.info("Orchestrator running")

        # 6. Run orchestrator
        result = await orchestrator.run(user_intent, self.workspace_meta)
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

