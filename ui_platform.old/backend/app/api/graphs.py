"""
graphs.py

Graph authoring and inspection endpoints.

Graphs are DAGs composed of:
- Nodes (stages / agents)
- Edges (execution flow)

Editing is restricted to developer mode.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.core.dependencies import get_current_user
from app.core.rbac import require_role
from app.schemas.graph import GraphCreate, GraphResponse
from app.api.workspaces import _WORKSPACES

router = APIRouter(tags=["graphs"])


@router.post("/{workspace}/graphs", response_model=GraphResponse)
async def create_graph(
    workspace: str,
    payload: GraphCreate,
    user=Depends(get_current_user),
):
    """
    Create or update a graph within a workspace.

    Graphs define execution topology.
    """
    require_role(user, "developer")

    ws = _WORKSPACES.get(workspace)
    if not ws:
        raise HTTPException(404, "Workspace not found")

    if ws["deployed"]:
        raise HTTPException(400, "Workspace is deployed and immutable")

    ws["graphs"][payload.name] = payload.model_dump()
    return payload.model_dump()


@router.get("/{workspace}/graphs/{graph_name}", response_model=GraphResponse)
async def get_graph(
    workspace: str,
    graph_name: str,
    user=Depends(get_current_user),
):
    """
    Retrieve a graph definition.

    Users may only retrieve graphs from deployed workspaces.
    """
    ws = _WORKSPACES.get(workspace)
    if not ws:
        raise HTTPException(404, "Workspace not found")

    if not ws["deployed"] and "developer" not in user["roles"]:
        raise HTTPException(403, "Workspace not deployed")

    graph = ws["graphs"].get(graph_name)
    if not graph:
        raise HTTPException(404, "Graph not found")

    return graph
