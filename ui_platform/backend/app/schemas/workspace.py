# -----------------------------------------------------------------------------
# Project: Agentic System UI Platform
# File: ui_platform/backend/app/schemas/workspace.py
#
# Description:
#   API schemas for workspace lifecycle management.
#
#   Workspaces are the top-level container for:
#     - graphs
#     - runs
#     - deployments
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-04
# -----------------------------------------------------------------------------

from typing import Optional, List
from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    """
    Request payload for creating a workspace.

    Used by:
      POST /workspaces
    """

    name: str = Field(..., min_length=3)
    description: Optional[str] = None


class WorkspaceUpdateRequest(BaseModel):
    """
    Request payload for updating workspace metadata.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    is_deployed: Optional[bool] = None


class WorkspaceResponse(BaseModel):
    """
    Full workspace representation returned to UI.
    """

    id: str
    name: str
    description: Optional[str]
    owner_id: str
    is_deployed: bool


class WorkspaceListResponse(BaseModel):
    """
    Response schema for workspace listings.
    """

    workspaces: List[WorkspaceResponse]
