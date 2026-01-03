from __future__ import annotations
from pathlib import Path
from typing import Dict

from runtime.runtime_manager import RuntimeManager
from runtime.session_manager import SessionManager
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient
from events.event_bus import EventBus

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class WorkspaceHub:
    """
    Global singleton that discovers and manages all workspaces.
    """

    _instance: WorkspaceHub | None = None

    def __new__(cls, workspaces_root: Path,
            model_manager: ModelManager,
            session_manager: SessionManager,
            tool_client: ToolClient,
            event_bus: EventBus):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, workspaces_root: Path,
            model_manager: ModelManager,
            session_manager: SessionManager,
            tool_client: ToolClient,
            event_bus: EventBus
    ):
        if self._initialized:
            return

        self.workspaces_root = workspaces_root
        self._runtimes: Dict[str, RuntimeManager] = {}
        self._initialized = True

        self.model_manager = model_manager
        self.session_manager = session_manager
        self.tool_client = tool_client
        self.event_bus = event_bus

        logger.info(f"WorkspaceHub initialized at {workspaces_root}")

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

    def get_runtime(
            self, 
            workspace_name: str
        ) -> RuntimeManager:
        if workspace_name in self._runtimes:
            return self._runtimes[workspace_name]

        workspace_dir = self.workspaces_root / workspace_name
        if not workspace_dir.exists():
            raise ValueError(f"Workspace not found: {workspace_name}")

        runtime = RuntimeManager(
            workspace_dir, 
            self.model_manager,
            self.session_manager, 
            self.tool_client,
            self.event_bus
        )
        self._runtimes[workspace_name] = runtime

        logger.info(f"Runtime loaded for workspace: {workspace_name}")
        return runtime

    def list_loaded_runtimes(self) -> list[str]:
        return list(self._runtimes.keys())


    

