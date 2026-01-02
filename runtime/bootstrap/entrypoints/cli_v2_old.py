#!/usr/bin/env python3
"""
cli.py

Command-line interface for launching and interacting with the multi-agent workspace runtime.

Features:
- List workspaces and agents
- Run a session for a workspace
- Support for hot reload of skills/contexts
- Debug and verbose logging
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer

from runtime.orchestrator import Orchestrator
from runtime.workspace_loader import WorkspaceLoader
from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
from runtime.graph_manager import GraphManager
from runtime.reload_manager import ReloadManager

app = typer.Typer(help="Agentic LLM CLI runtime")


# -------------------------
# Global Configuration
# -------------------------

WORKSPACES_DIR = Path("workspaces")
DEFAULT_LLM = "openai-gpt"  # placeholder for actual LLM instance


# -------------------------
# CLI Commands
# -------------------------

@app.command()
def list_workspaces():
    """List all available workspaces"""
    workspaces = [p.name for p in WORKSPACES_DIR.iterdir() if p.is_dir()]
    typer.echo("Available workspaces:")
    for ws in workspaces:
        typer.echo(f"- {ws}")


@app.command()
def list_agents(workspace: str):
    """List all agents in a workspace"""
    workspace_dir = WORKSPACES_DIR / workspace
    if not workspace_dir.exists():
        typer.echo(f"Workspace not found: {workspace}")
        raise typer.Exit(1)

    loader = WorkspaceLoader(workspace_dir)
    agents = loader.list_agents()
    typer.echo(f"Agents in workspace '{workspace}':")
    for a in agents:
        typer.echo(f"- {a}")


@app.command()
def run(
    workspace: str,
    session_id: Optional[str] = None,
    verbose: bool = False,
    reload: bool = False,
):
    """
    Run a session for the given workspace.
    """
    workspace_dir = WORKSPACES_DIR / workspace
    if not workspace_dir.exists():
        typer.echo(f"Workspace not found: {workspace}")
        raise typer.Exit(1)

    asyncio.run(_run_workspace_session(workspace_dir, session_id, verbose, reload))


# -------------------------
# Async Runtime Execution
# -------------------------

async def _run_workspace_session(
    workspace_dir: Path, session_id: Optional[str], verbose: bool, reload: bool
):
    """
    Loads workspace, agents, stages, builds graph, and runs orchestrator.
    """

    print(f"[CLI] Loading workspace: {workspace_dir.name}")

    # 1. Load workspace metadata
    workspace_loader = WorkspaceLoader(workspace_dir)
    workspace_meta = workspace_loader.load_workspace()
    print(f"[CLI] Workspace metadata loaded: {workspace_meta.get('name')}")

    # 2. Register agents
    agent_registry = AgentRegistry(workspace_dir)
    agent_registry.load_agents()
    print(f"[CLI] Registered agents: {agent_registry.roles()}")

    # 3. Register stages
    stage_registry = StageRegistry(workspace_dir)
    stage_registry.load_stages()
    print(f"[CLI] Stages loaded: {stage_registry.list_stages()}")

    # 4. Initialize GraphManager
    graph_manager = GraphManager(agent_registry, stage_registry)
    execution_graph = graph_manager.build_graph()
    print("[CLI] Graph built successfully")

    # 5. Optional reload manager
    if reload:
        reload_manager = ReloadManager(workspace_dir, agent_registry)
        reload_manager.start_periodic_reload()
        print("[CLI] Hot-reload enabled for skills/context")

    # 6. Initialize orchestrator
    orchestrator = Orchestrator(
        graph=execution_graph,
        workspace_dir=workspace_dir,
        agent_registry=agent_registry,
        stage_registry=stage_registry,
    )

    # 7. Run session
    session_id = session_id or f"session_{asyncio.get_event_loop().time()}"
    print(f"[CLI] Starting session: {session_id}")

    final_state = await orchestrator.run_session(session_id=session_id)

    print(f"[CLI] Session complete. Final state:")
    if verbose:
        print(json.dumps(final_state, indent=2))
    else:
        print(final_state)


# -------------------------
# Entry Point
# -------------------------

if __name__ == "__main__":
    app()

