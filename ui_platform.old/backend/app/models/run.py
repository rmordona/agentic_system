"""
run.py

Execution run domain models.

Responsibilities:
- Track execution of a graph
- Support SSE streaming
- Enable observability and replay

Runs are immutable execution records.
"""

from typing import Dict, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class Run(BaseModel):
    """
    Execution run record.

    Each run corresponds to a single invocation
    of a workspace graph.
    """

    id: str = Field(..., description="Run unique identifier")
    workspace_id: str
    graph_id: str

    status: RunStatus = "pending"

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    initiated_by: str = Field(..., description="User ID")

    input_payload: Optional[Dict[str, Any]] = None
    output_payload: Optional[Dict[str, Any]] = None

    error: Optional[str] = None


class RunCreate(BaseModel):
    """
    Payload to initiate a run.
    """

    workspace_id: str
    graph_id: str
    input_payload: Optional[Dict[str, Any]] = None


class RunEvent(BaseModel):
    """
    SSE event model for live execution updates.
    """

    run_id: str
    stage_id: Optional[str] = None
    status: RunStatus
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
