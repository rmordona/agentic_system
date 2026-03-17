from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any, Literal

from runtime.engine.domain.task import Task, HITLState
from runtime.engine.domain.envelopes import DataEnvelope, ToolEnvelope


@dataclass
class ArtifactSchema:
    # ---- Identity ----
    role: str| None = None
    purpose: str| None = None
    mission: str| None = None
    session_id: str| None = None

    # ---- Versioning ----
    schema_version: Literal["1.0"] = "1.0"

    status: Literal[
        "initialized",
        "running",
        "blocked",
        "completed",
        "aborted"
    ] =  "initialized"

    # ---- Used per tool to determine stage-exit policy
    stage_exit_allowed: bool| None = None

    # ---- Planning ----
    current_stage: str| None = None
    current_plan: List[Task] = field(default_factory=list)
    plan_history: List[Dict] = field(default_factory=list)

    # Open tasks are tasks that haven't been executed or completed yet
    open_tasks: List[Task] = field(default_factory=list)

    # ---- Knowledge ----
    spec: Optional[Dict] | None = None
    constraints: Dict = field(default_factory=dict)

    # ---- Proposals ----
    proposals: List[Dict] = field(default_factory=list)
    accepted_proposals: List[Dict] = field(default_factory=list)
    rejected_proposals: List[Dict] = field(default_factory=list)

    # ---- Clarifications ----
    open_questions: List[Dict] = field(default_factory=list)
    resolved_questions: List[Dict] = field(default_factory=list)

    # ---- Validation ----
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ---- Human-in-the-loop ----
    hitl: HITLState = field(default_factory=HITLState)

    # ---- Timestamps ----
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentContext:
    agent_name: str
    stage_name: str
    control_raw: ArtifactSchema = field(default_factory=ArtifactSchema)
    data_raw: Optional[DataEnvelope] = None
    tool_raw: List[ToolEnvelope] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    result_summary: Optional[str] = None
