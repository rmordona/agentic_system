"""
workspace.py

Workspace domain models.

Responsibilities:
- Represent agent workspaces
- Define deployment boundaries
- Support developer vs production usage

A workspace is the top-level container for graphs, stages, and runs.
"""

from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Workspace(BaseModel):
    """
    Workspace definition.

    Workspaces map directly to:
    - agentic_system/workspaces/*
    """

    id: str = Field(..., description="Workspace unique identifier")
    name: str
    description: Optional[str] = None

    owner_id: str = Field(..., description="User who owns this workspace")
    is_deployed: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class WorkspaceCreate(BaseModel):
    """
    Payload for creating a workspace.
    """

    name: str
    description: Optional[str] = None


class WorkspaceSummary(BaseModel):
    """
    Lightweight workspace projection for UI lists.
    """

    id: str
    name: str
    is_deployed: bool
