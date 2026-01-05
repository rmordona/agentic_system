"""
runs.py

Execution endpoints for graph runs.

A run represents:
- One invocation of a graph
- With input parameters
- Producing stage-by-stage execution events
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import uuid4
from pydantic import BaseModel
from app.core.dependencies import get_current_user
from app.api.workspaces import _WORKSPACES

router = APIRouter(tags=["runs"])

# Temporary in-memory storage for demo purposes
_RUNS = {}

class RunPayload(BaseModel):
    """
    Request payload for executing a graph.
    """
    inputs: dict


async def execute_graph(run_id: str, workspace: str, graph: str, payload: dict):
    """
    Simulate execution of a graph stage by stage.
    Update _RUNS with stage events and final status.
    """
    stages = ["stage1", "stage2", "stage3"]  # Replace with actual stages from the graph
    for stage in stages:
        _RUNS[run_id]["events"].append({"stage": stage, "status": "running"})
        # Simulate some work
        import asyncio
        await asyncio.sleep(1)
    _RUNS[run_id]["status"] = "completed"


@router.post("/{workspace}/{graph}/run")
async def run_graph(
    workspace: str,
    graph: str,
    payload: RunPayload,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """
    Execute a deployed graph asynchronously.
    """
    ws = _WORKSPACES.get(workspace)
    if not ws or not ws["deployed"]:
        raise HTTPException(400, "Workspace not deployed")

    if graph not in ws["graphs"]:
        raise HTTPException(404, "Graph not found")

    run_id = str(uuid4())
    _RUNS[run_id] = {
        "workspace": workspace,
        "graph": graph,
        "status": "running",
        "events": [],
    }

    # Launch background execution
    background_tasks.add_task(execute_graph, run_id, workspace, graph, payload.inputs)

    return {"run_id": run_id}


@router.get("/{run_id}")
async def get_run_status(run_id: str):
    """
    Retrieve the status and events of a specific run.
    """
    run = _RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run
