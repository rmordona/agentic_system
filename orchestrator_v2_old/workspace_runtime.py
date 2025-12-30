# workspace_runtime.py

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from events.event_bus import EventBus
from orchestrator import Orchestrator
from workspace_loader import WorkspaceLoader
from agent_registry import AgentRegistry
from stage_registry import StageRegistry
from graph_manager import GraphManager
from reload_manager import ReloadManager

class WorkspaceRuntime:
    """
    Manages multiple workspaces and orchestrates sessions per workspace.
    - Each workspace has its own stages.json, agent artifacts, compiled graph.
    - Each session gets a dedicated Orchestrator and State.
    """

    def __init__(self, workspace_root: Path, event_bus: Optional[EventBus] = None):
        self.workspace_root = workspace_root
        self.event_bus = event_bus or EventBus()

        # Workspace-level registries and loaders
        self.workspaces: Dict[str, WorkspaceLoader] = {}
        self.agent_registries: Dict[str, AgentRegistry] = {}
        self.stage_registries: Dict[str, StageRegistry] = {}
        self.graph_managers: Dict[str, GraphManager] = {}
        self.reload_managers: Dict[str, ReloadManager] = {}

        # Active orchestrators per session
        self.active_sessions: Dict[str, Orchestrator] = {}

        self._load_workspaces()

    def _load_workspaces(self):
        for ws_dir in self.workspace_root.iterdir():
            if ws_dir.is_dir():
                ws_name = ws_dir.name
                loader = WorkspaceLoader(ws_dir)
                loader.load_workspace()
                self.workspaces[ws_name] = loader

                # Registries
                agent_registry = AgentRegistry(loader.agent_paths())
                agent_registry.load_agents()
                self.agent_registries[ws_name] = agent_registry

                stage_registry = StageRegistry(loader.stage_path)
                stage_registry.load_stages()
                self.stage_registries[ws_name] = stage_registry

                # Graph
                graph_manager = GraphManager(agent_registry, stage_registry)
                graph_manager.build_graph()
                self.graph_managers[ws_name] = graph_manager

                # Reload manager
                reload_manager = ReloadManager(loader, agent_registry, stage_registry, graph_manager)
                reload_manager.start()
                self.reload_managers[ws_name] = reload_manager

    def start_session(self, session_id: str, workspace_name: str, task: str) -> Orchestrator:
        if workspace_name not in self.workspaces:
            raise ValueError(f"Workspace '{workspace_name}' not loaded")

        agent_registry = self.agent_registries[workspace_name]
        stage_registry = self.stage_registries[workspace_name]
        graph = self.graph_managers[workspace_name].graph

        orchestrator = Orchestrator(
            event_bus=self.event_bus,
            agent_registry=agent_registry,
            stage_registry=stage_registry,
            graph_builder=lambda ar, sr: graph  # Use pre-built graph
        )

        self.active_sessions[session_id] = orchestrator

        # Initial run is async; caller can await orchestrator.run(session_id, task)
        return orchestrator

    async def run_session(self, session_id: str, workspace_name: str, task: str) -> Dict[str, Any]:
        orchestrator = self.start_session(session_id, workspace_name, task)
        return await orchestrator.run(session_id, task)

    def stop_session(self, session_id: str):
        if session_id in self.active_sessions:
            # Cleanup if needed
            del self.active_sessions[session_id]

    def reload_workspace(self, workspace_name: str):
        """
        Trigger workspace reload on demand.
        """
        if workspace_name not in self.workspaces:
            raise ValueError(f"Workspace '{workspace_name}' not loaded")

        loader = self.workspaces[workspace_name]
        loader.load_workspace()

        # Reload agents and stages
        agent_registry = self.agent_registries[workspace_name]
        agent_registry.reload_agents(loader.agent_paths())

        stage_registry = self.stage_registries[workspace_name]
        stage_registry.reload_stages(loader.stage_path)

        # Rebuild graph
        graph_manager = self.graph_managers[workspace_name]
        graph_manager.build_graph()

