from __future__ import annotations
from core.paths import WORKSPACES_ROOT

import asyncio
from pathlib import Path
from typing import Dict
from runtime.bootstrap.runtime_manager import RuntimeManager
from runtime.bootstrap.session_manager import SessionManager
from events.event_bus import EventBus

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class WorkspaceHub:
    """
    Global singleton that discovers and manages all workspaces.
    """

    def __init__(self, 
            session_manager: SessionManager,
            event_bus: EventBus
    ):
        self._runtimes = {}
        self._locks = {}
        self.workspaces_root = WORKSPACES_ROOT
        self._runtimes: Dict[str, RuntimeManager] = {}
        self.session_manager = session_manager
        self.event_bus = event_bus

        logger.info(f"WorkspaceHub initialized at {self.workspaces_root}")

    # --------------------------------------------------
    # Discovery
    # --------------------------------------------------

    def discover_workspaces(self) -> list[str]:
        workspaces = [
            p.name
            for p in self.workspaces_root.iterdir()
            if p.is_dir() and (p / "workspace.json").exists()
        ]
        logger.info(f"Discovered workspaces: {workspaces}")
        return workspaces

    # --------------------------------------------------
    # Runtime access
    # --------------------------------------------------

    async def get_runtime(self, workspace_name: str) -> RuntimeManager:

        if workspace_name in self._runtimes:
            return self._runtimes[workspace_name]

        # Ensure only one initializer runs
        lock = self._locks.setdefault(workspace_name, asyncio.Lock())

        async with lock:
            # Double-check after acquiring lock
            if workspace_name in self._runtimes:
                return self._runtimes[workspace_name]

            runtime = RuntimeManager(
                workspace_name, 
                self.session_manager, 
                self.event_bus
            )
            await runtime.initialize()
    
            self._runtimes[workspace_name] = runtime

            logger.info(f"Runtime loaded for workspace: {workspace_name}")
            return runtime

    def list_loaded_runtimes(self) -> list[str]:
        return list(self._runtimes.keys())


    

