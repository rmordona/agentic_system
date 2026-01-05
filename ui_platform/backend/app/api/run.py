"""
runs.py

Execution endpoints for graph runs.

A run represents:
- One invocation of a graph
- With input parameters
- Producing stage-by-stage execution events
"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import uuid4
from app.core.dependencies import get_current_user
from app.api.workspaces import _WORKSPACES

router = APIRouter(tags=["runs"])

_RUNS = {}


@router.post("/{workspace}/{graph}/run")
async def run_graph(
    workspace: str,
    graph: str,
    payload: dict,
    user=Depends(get_current_user),
):
    """
    Execute a deployed graph.

    This endpoint triggers execution asynchronously.
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

    # TODO: Trigger your actual agent runtime here
    return {"run_id": run_id}
