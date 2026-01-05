# -----------------------------------------------------------------------------
# Project: Agentic System UI Platform
# File: ui_platform/backend/app/schemas/graph.py
#
# Description:
#   API schemas for graph creation, editing, and retrieval.
#
#   Graphs are React Flow–compatible representations of
#   agent execution pipelines.
#
#   These schemas intentionally mirror React Flow's node/edge format
#   to minimize UI transformation logic.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-04
# -----------------------------------------------------------------------------

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# -----------------------------
# React Flow Node / Edge Schemas
# -----------------------------

class GraphNodeSchema(BaseModel):
    """
    React Flow–compatible node schema.

    Each node usually maps to:
      - a stage
      - an agent
      - a tool invocation
    """

    id: str
    type: str = Field(default="stage")
    position: Dict[str, float]
    data: Dict[str, Any]


class GraphEdgeSchema(BaseModel):
    """
    React Flow–compatible edge schema.
    """

    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: bool = False


# -----------------------------
# Graph API Schemas
# -----------------------------

class GraphCreateRequest(BaseModel):
    """
    Request payload for creating a new graph.
    """

    workspace_id: str
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]


class GraphUpdateRequest(BaseModel):
    """
    Request payload for updating an existing graph.

    Supports partial updates.
    """

    nodes: Optional[List[GraphNodeSchema]] = None
    edges: Optional[List[GraphEdgeSchema]] = None


class GraphResponse(BaseModel):
    """
    Full graph representation returned to UI.
    """

    id: str
    workspace_id: str
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]


class GraphListResponse(BaseModel):
    """
    Response schema for listing graphs under a workspace.
    """

    graphs: List[GraphResponse]
