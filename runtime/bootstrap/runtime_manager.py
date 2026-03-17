from __future__ import annotations
from core.paths import RUNTIME_ROOT, GLOBAL_CONFIG_PATH

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional, Any

from runtime.bootstrap.workspace_loader import WorkspaceLoader
from runtime.bootstrap.session_manager import SessionManager, SessionContext
from runtime.core_engine import CoreEngine
from runtime.runtime_context import RuntimeContext
from runtime.reload_manager import ReloadManager
from runtime.orchestrator import Orchestrator

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
            workspace_name: str,
            session_manager: SessionManager,
            event_bus: EventBus,
        ):
        ws_name = workspace_name
        if ws_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[ws_name] = instance
        return cls._instances[ws_name]

    def __init__(self, 
            workspace_name: str,
            session_manager: SessionManager,
            event_bus: EventBus,
        ):

        if hasattr(self, "_initialized") and self._initialized:
            return  # Avoid re-initialization
 
        self._initialized = True

        # ---- Per-session storage ----
        self._orchestrators: Dict[str, Orchestrator] = {}

        '''
        self.workspace_path = WORKSPACES_ROOT / workspace_name
  
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace not found: {workspace_name}")
        '''

        self.runtime_path = RUNTIME_ROOT
        #self.workspace_name = workspace_name
        self.session_manager = session_manager
        self.event_bus = event_bus

        '''
        logger.info(f"Initializing Runtime Agent: {self.workspace_name}... ")

        # Load Workspace Configuration (workspace.json)
        self.workspace_meta = WorkspaceLoader(self.workspace_name).load_workspace()
        logger.info(f"Workspace metadata loaded: {self.workspace_meta.get('name')}")

        self.reload_manager = ReloadManager(
            workspace_loaders={self.workspace_name: self.workspace_meta},
            interval_seconds=30
        )
        
        self.reload_manager.start_periodic_reload()
        logger.info("Hot-reload enabled for skills/context")
        '''

        # Note: async initialization will be called from workspace_hub
        self.core_engine = CoreEngine(
            # workspace_name=self.workspace_name,
            # workspace_meta=self.workspace_meta
        )

    # ------------------------------------------------------------------
    # Initialized from workspace_hub.py at bootstrap
    # ------------------------------------------------------------------
    async def initialize(self):
        logger.info("Initializing Core Engine ...")
        await self.core_engine.initialize()

        self.compiled_graph = self.core_engine.compile()

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
                # workspace_name=self.workspace_name,
                core_engine=self.core_engine,
                session_id=session_ctx.session_id,
                event_bus=self.event_bus
            )
            self._orchestrators[session_ctx.session_id] = orchestrator
        return orchestrator

    # ------------------------------------------------------------------
    # Run the stream
    # ------------------------------------------------------------------
    async def run_stream(
        self,
        user_id: str,
        user_intent: str,
        session_id: Optional[str] = None
    ):
        """
        Stream LangGraph events for the user message.
        Yields dictionaries to send over WebSocket.
        """
        # 1. Create or fetch session
        if session_id and self.session_manager.exists(user_id, session_id):
            session_ctx = self.session_manager.get(session_id)
        else:
            session_ctx = self.session_manager.create_session(user_id)
        session_id = session_ctx.session_id

        # Persist Session Id right away
        yield {
            "type": "session_update",
            "session_id": session_id
        }

        orchestrator = self.get_orchestrator(session_ctx)

        logger.info(f"Run: Session ID: {session_id}")

        # 2. Run LangGraph stream
        iter = 0
        async for event in orchestrator.run_stream(user_intent, session_id):
            iter += 1
            # Each event can be a token, tool update, or status update
            yield {
                "type": "event",
                "iteration": iter,
                "event": event
            }

        # After completion, yield final content
        final_content = getattr(orchestrator.initial_state, "final_content", "No response")
        yield {
            "type": "completion",
            "content": final_content
        }


    # ------------------------------------------------------------------
    # Resuming the stream
    # ------------------------------------------------------------------
    async def resume_stream(
        self,
        human_input: str,
        session_id: str,
    ):
        """
        Resume an interrupted LangGraph stream (HITL).
        Yields websocket-ready events.
        """

        logger.info(f"Resume: Session ID: {session_id}")

        # Retrieve session context
        session_ctx = self.session_manager.get(session_id)
        orchestrator = self.get_orchestrator(session_ctx)

        iter_count = 0

        async for event in orchestrator.resume_stream(human_input, session_id):
            iter_count += 1

            yield {
                "type": "event",
                "iteration": iter_count,
                "event": event,
            }

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

