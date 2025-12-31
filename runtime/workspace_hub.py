from __future__ import annotations
from pathlib import Path
from typing import Dict

from runtime.runtime_manager import RuntimeManager
from runtime.session_manager import SessionManager
from runtime.memory_manager import MemoryManager
from runtime.embeddings.base import EmbeddingStore
from llm.local_llm import LocalLLMChatModel
from runtime.tools.client import ToolClient
from runtime.logger import AgentLogger

from events.event_bus import EventBus

class WorkspaceHub:
    """
    Global singleton that discovers and manages all workspaces.
    """

    _instance: WorkspaceHub | None = None

    def __new__(cls, workspaces_root: Path,
            llm: LocalLLMChatModel,
            session_manager: SessionManager,
            memory_manager: MemoryManager, 
            embedding_store: EmbeddingStore, 
            tool_client: ToolClient,
            event_bus: EventBus):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, workspaces_root: Path,
            llm: LocalLLMChatModel,
            session_manager: SessionManager,
            memory_manager: MemoryManager, 
            embedding_store: EmbeddingStore, 
            tool_client: ToolClient,
            event_bus: EventBus
    ):
        if self._initialized:
            return

        self.workspaces_root = workspaces_root
        self._runtimes: Dict[str, RuntimeManager] = {}
        self._initialized = True

        self.llm = llm
        self.session_manager = session_manager
        self.memory_manager = memory_manager
        self.embedding_store = embedding_store
        self.tool_client = tool_client
        self.event_bus = event_bus

        # 🔑 Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger( workspace=None, component="system" )

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
            self.llm,
            self.session_manager, 
            self.memory_manager, 
            self.embedding_store, 
            self.tool_client,
            self.event_bus
        )
        self._runtimes[workspace_name] = runtime

        logger.info(f"Runtime loaded for workspace: {workspace_name}")
        return runtime

    def list_loaded_runtimes(self) -> list[str]:
        return list(self._runtimes.keys())


    

