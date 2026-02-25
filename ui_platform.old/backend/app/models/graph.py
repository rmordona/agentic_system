"""
graph.py

Graph and workflow domain models.

Responsibilities:
- Represent React Flow nodes and edges
- Encode stage execution topology
- Support observability overlays

These models are React Flow–compatible by design.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# -------------------------
# React Flow Primitives
# -------------------------

class GraphNode(BaseModel):
    """
    Node in the execution graph.

    Maps directly to a stage in stages.json.
    """

    id: str
    type: str = Field(default="stage")
    position: Dict[str, float]
    data: Dict[str, Any]

    def is_agent_node(self) -> bool:
        """
        Check whether this node represents an agent stage.
        """
        return self.type == "stage"


class GraphEdge(BaseModel):
    """
    Edge connecting two graph nodes.
    """

    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: bool = False


# -------------------------
# Graph Containers
# -------------------------

class GraphDefinition(BaseModel):
    """
    Full graph definition.

    Used by:
    - React Flow editor
    - Runtime execution planner
    """

    id: str
    workspace_id: str

    nodes: List[GraphNode]
    edges: List[GraphEdge]

    created_at: str


class GraphUpdate(BaseModel):
    """
    Payload for updating a graph.

    Used when editing nodes or edges in UI.
    """

    nodes: Optional[List[GraphNode]] = None
    edges: Optional[List[GraphEdge]] = None
