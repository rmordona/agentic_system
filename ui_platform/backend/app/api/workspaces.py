"""
workspaces.py

Workspace management endpoints.

A workspace represents a logical container for:
- Graphs
- Stages
- Runs
- Agent configurations

Only developers may create or modify workspaces.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from app.core.dependencies import get_current_user
from app.core.rbac import require_role
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(tags=["workspaces"])

_WORKSPACES: Dict[str, Dict] = {}


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    payload: WorkspaceCreate,
    user=Depends(get_current_user),
):
    """
    Create a new workspace.

    Access:
        Developer only

    A workspace is mutable until deployed.
    """
    require_role(user, "developer")

    if payload.name in _WORKSPACES:
        raise HTTPException(400, "Workspace already exists")

    _WORKSPACES[payload.name] = {
        "name": payload.name,
        "owner": user["sub"],
        "graphs": {},
        "deployed": False,
    }

    return _WORKSPACES[payload.name]


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(user=Depends(get_current_user)):
    """
    List all workspaces visible to the user.

    Developers see all.
    Users see only deployed workspaces.
    """
    if "developer" in user["roles"]:
        return list(_WORKSPACES.values())

    return [w for w in _WORKSPACES.values() if w["deployed"]]


@router.post("/{name}/deploy")
async def deploy_workspace(name: str, user=Depends(get_current_user)):
    """
    Deploy a workspace into immutable runtime mode.

    After deployment:
    - Graphs become read-only
    - Workspace is visible to users
    """
    require_role(user, "developer")

    if name not in _WORKSPACES:
        raise HTTPException(404, "Workspace not found")

    _WORKSPACES[name]["deployed"] = True
    return {"status": "deployed"}
