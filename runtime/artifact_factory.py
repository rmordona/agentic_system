# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/artifacts/artifact_factory.py
#
# Description:
#   This module defines the canonical parser and compiler for artifact
#   specifications authored in Markdown.
#
#   An artifact represents the *shared, evolving state* that agents reason
#   about and modify across stages of an agentic pipeline.
#
#   This factory is intentionally:
#     - Agent-agnostic
#     - Stage-agnostic
#     - Domain-agnostic
#
#   It performs **structural extraction**, not interpretation.
#
#   Responsibilities:
#     - Parse artifact Markdown into a structured, typed schema
#     - Extract planning directives embedded in human-readable text
#     - Preserve raw content for LLM context
#
#   This module does NOT:
#     - Decide which agent owns the artifact
#     - Enforce workflow transitions
#     - Validate semantic correctness of plans
#
#   Chain of custody:
#
#     Artifact.md (human-readable state)
#        ↓ deterministic parsing
#     ArtifactSchema (typed runtime state)
#
# Production Guarantees:
#   - Deterministic Markdown parsing via AST
#   - Typed validation using Pydantic
#   - Zero hidden mutation
#   - Full raw-content preservation for audit and replay
#
################################################################################
# Artifact–Agent Relationship Patterns in a Chain-of-Custody Architecture
#
# In a production-grade agentic system, the relationship between Agents and
# Artifacts is not limited to a simple 1:1 mapping. While that pattern is useful
# for narrow, isolated tasks, a true Chain-of-Custody architecture supports
# multiple coordination patterns that scale to real-world workflows.
#
# The guiding mental model is:
#
#   Artifact = Patient Record (canonical, evolving source of truth)
#   Agent    = Specialist (authorized decision-maker with bounded expertise)
#
# Agents never replace the artifact; they examine it, reason over it, and
# propose controlled updates. The artifact remains the single authoritative
# state across all stages.
#
# ---------------------------------------------------------------------------
# Pattern A: Many Agents → One Artifact (Collaborative / Assembly Line)
#
# This is the most common pattern in agentic workflows.
#
# A single artifact serves as shared state, while multiple agents contribute
# sequentially or conditionally based on their role and authority.
#
# Example:
#   Artifact: software_spec.md
#
#   - Architect Agent: defines ## Requirements
#   - Security Agent: adds ## Security Constraints
#   - Developer Agent: implements ## Implementation
#
# The ArtifactFactory and orchestrator determine which agent is active by
# inspecting structural cues (e.g., headings, role tags, or plan directives).
#
# This pattern enables progressive refinement while preserving auditability.
#
# ---------------------------------------------------------------------------
# Pattern B: One Agent → Many Artifacts (Managerial / Supervisory)
#
# A high-authority agent may be responsible for maintaining consistency across
# a suite of related artifacts.
#
# Example:
#   Agent: Project Manager
#
#   - roadmap.md   (high-level milestones)
#   - tasks.md     (granular execution plan)
#   - budget.md    (resource allocation)
#
# The agent operates with a broader context and ensures cross-artifact
# invariants (e.g., new tasks update both roadmap and budget).
#
# This pattern supports coordination, synchronization, and governance.
#
# ---------------------------------------------------------------------------
# Pattern C: One Agent → One Artifact (Specialized / Isolated)
#
# Used for focused sub-tasks where isolation improves quality and safety.
#
# Example:
#   Agent: SQL Optimizer
#   Artifact: query_plan.md
#
# The agent receives only the information required for the task, preventing
# distraction, scope creep, or unintended side effects.
#
# ---------------------------------------------------------------------------
# Summary
#
# Relationship   | Name         | Primary Use Case
# ---------------|--------------|---------------------------------------------
# 1 : 1          | Specialist   | Deep, narrow tasks (e.g., refactoring)
# Many : 1       | Assembly Line| Progressive builds (spec → design → code)
# 1 : Many       | Orchestrator | Cross-artifact coordination and governance
#
# These patterns are first-class citizens in a Chain-of-Custody architecture
# and are enabled by strict separation of policy (agents), state (artifacts),
# execution (orchestrator), and observability (ledger and streams).
################################################################################
#
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Schema Definitions
# -------------------------------------------------------------------------

################################################################################
# Artifacts vs. Bodies of Work in a Chain-of-Custody Architecture
#
# In an agentic system, the artifact.md is not the work itself.
# It is the *control plane* that governs, describes, and constrains the work.
#
# The "Body" is the executable, legal, financial, or operational substrate
# where real-world effects occur. The artifact exists to:
#   - Define intent
#   - Encode rules and constraints
#   - Track decisions and evolution
#   - Provide auditable context for agents
#
# Agents reason over the artifact, then act upon or generate the body.
# The body may change formats, tools, or storage systems; the artifact
# remains stable, human-readable, and versionable.
#
# ---------------------------------------------------------------------------
# Comparative Examples
#
# Domain        | Control Artifact (artifact.md)        | Body (The Work)
# --------------|---------------------------------------|-----------------------------
# Legal         | Compliance Checklist                  | Contract (.docx / .pdf)
# Data Eng      | ETL Pipeline Status                   | Database Schema / Records
# FinOps        | Budgeting Rules & Allocations         | Spreadsheet (.xlsx / .csv)
# Procurement  | Vendor Evaluation Criteria             | RFQ (Request for Quote)
# DevOps        | Deployment Roadmap                    | Infrastructure (Terraform / YAML)
#
# ---------------------------------------------------------------------------
# Architectural Implications
#
# - Artifacts are lightweight, textual, and agent-readable
# - Bodies are heavyweight, tool-specific, and execution-bound
# - Artifacts *govern* bodies; they do not replace them
# - Multiple bodies may be governed by a single artifact
#
# This separation enables:
#   - Clear chain of custody
#   - Multi-agent collaboration without file contention
#   - Auditable reasoning and replay
#   - Safe automation over high-impact systems
#
# In short:
#   Artifacts think.
#   Bodies execute.
################################################################################

import re
import mistune
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import uuid4

#from runtime.agent_profiler import AgentProfile

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import UUID


class Task(BaseModel):
    id: str
    description: str
    stage: str
    execution: Literal["tool", "llm"] = "tool"
    tool_name: str = ""
    depends_on: List[str] = []
    status: Literal["pending", "done", "blocked", "completed"] = "pending"
    result: dict | None = None
    error: str | None = None
    reason: str | None = None


class HITLState(BaseModel):
    required: bool = False
    approved: Optional[bool] = None
    comments: Optional[str] = None


class ArtifactSchema(BaseModel):
    # ---- Versioning ----
    schema_version: Literal["1.0"] = "1.0"

    # ---- Identity ----

    role: str
    purpose: str

    mission: str
    session_id: str
    status: Literal[
        "initialized",
        "running",
        "blocked",
        "completed",
        "aborted"
    ]

    # ---- Used per tool to determine stage-exit policy
    stage_exit_allowed: bool

    # ---- Planning ----
    current_stage: str
    current_plan: List[Task] = Field(default_factory=list)
    plan_history: List[Dict] = Field(default_factory=list)

    # Open tasks are tasks that haven't been executed or completed yet
    open_tasks: List[Task] = Field(default_factory=list)

    # ---- Knowledge ----
    spec: Optional[Dict] = None
    constraints: Dict = Field(default_factory=dict)

    # ---- Proposals ----
    proposals: List[Dict] = Field(default_factory=list)
    accepted_proposals: List[Dict] = Field(default_factory=list)
    rejected_proposals: List[Dict] = Field(default_factory=list)

    # ---- Clarifications ----
    open_questions: List[Dict] = Field(default_factory=list)
    resolved_questions: List[Dict] = Field(default_factory=list)

    # ---- Validation ----
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # ---- Human-in-the-loop ----
    hitl: HITLState = Field(default_factory=HITLState)

    # ---- Timestamps ----
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# -------------------------------------------------------------------------
# Artifact Factory
# -------------------------------------------------------------------------

class ArtifactFactory:
    """
    Compiles artifact Markdown into validated Artifact objects.
    """

    artifact: ArtifactSchema = None

    def __init__(self, artifact: ArtifactSchema):

        if artifact is not None:
            self.artifact = artifact
        else:
            self.parser = mistune.create_markdown(renderer=None)
            logger.info("ArtifactFactory initialized")

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _parse_plan_line(self, line: str) -> Optional[Task]:
        logger.debug("Parsing plan line", extra={"line": line})

        match = re.search(r"-\s*\[\s*\]\s*(.*?)\s*#\s*stage:\s*(\S+)", line)
        if not match:
            return None

        task_text = match.group(1).strip()
        stage = match.group(2).strip()

        return Task(
            id=hashlib.sha1(task_text.encode()).hexdigest()[:12],
            description=task_text,
            stage=stage,
            status="pending"
        )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    @staticmethod
    def show_tasks(tasks: list):
        logger.console("\nList of Open Tasks:")
        for task in tasks:
            logger.console(f"- [ ] {task.id}: {task.description}")


    @staticmethod
    def initialize_from_agent(agent_profile: Any, session_id: str = None) -> ArtifactSchema:
        """
        Creates the starting point for a pipeline execution 
        based on a specific Agent's profile.
        """
        return ArtifactSchema(
            # Identity mapped from AGENT.md
            role=agent_profile.role,
            purpose=agent_profile.description,
            mission=f"Execute task as {agent_profile.name}",

            # Stage Exit
            stage_exit_allowed = False,
            
            # Session & State
            session_id=session_id or str(uuid4()),
            status="initialized",
            
            # Planning
            current_stage="--INIT--", # Or your pipeline entry_stage
            
            # Knowledge (Initial empty containers)
            spec=None, 
            constraints={
                "forbidden_actions": agent_profile.forbidden_actions,
                "max_iterations": agent_profile.max_iterations,
                "authority": agent_profile.authority_notes
            }
        )

    def compile(self, md_text: str) -> ArtifactSchema:
        """
        Compiles Markdown text directly into an ArtifactSchema.
        """
        logger.info("Compiling artifact")

        ast = self.parser(md_text)

        role = None
        purpose = None
        mission = None
        session_id = "unknown"
        status = "initialized"
        current_stage = "unknown"

        current_plan: List[Task] = []

        current_section: Optional[str] = None

        for node in ast:
            if node["type"] == "heading":
                current_section = "".join(
                    c.get("text", "") for c in node.get("children", [])
                ).lower()
                continue

            if node["type"] == "list" and "current plan" in (current_section or ""):
                for item in node.get("children", []):
                    try:
                        line_text = item["children"][0]["children"][0]["text"]
                    except (KeyError, IndexError, TypeError):
                        logger.warning("Malformed plan entry")
                        continue

                    task = self._parse_plan_line(line_text)
                    if task:
                        current_plan.append(task)

            if node["type"] == "paragraph":
                text = "".join(c.get("text", "") for c in node.get("children", []))

                if text.lower().startswith("role:"):
                    role = text.split(":", 1)[1].strip()
                if text.lower().startswith("purpose:"):
                    purpose = text.split(":", 1)[1].strip()

                if text.lower().startswith("mission:"):
                    mission = text.split(":", 1)[1].strip()

                if text.lower().startswith("session_id:"):
                    session_id = text.split(":", 1)[1].strip()

                if text.lower().startswith("status:"):
                    status = text.split(":", 1)[1].strip()

        artifact = ArtifactSchema(
            role=role or "unknown",
            purpose=purpose or "unknown",
            mission=mission or "unknown",
            session_id=session_id,
            status=status,
            current_stage=current_stage,
            current_plan=current_plan,
            raw_content=md_text
        )

        logger.info(
            "ArtifactSchema compiled successfully",
            extra={
                "role" : artifact.role,
                "purpose" : artifact.purpose,
                "mission": artifact.mission,
                "tasks": len(artifact.current_plan)
            }
        )

        self.artifact = artifact

        return artifact

    def get_next_task_for_stage(self, role: str):
        _role = self.artifact.role
        _current_stage = self.artifact.current_stage
        _current_plan = self.artifact.current_plan
        pass


# -------------------------------------------------------------------------
# Artifact Validator
# -------------------------------------------------------------------------

class ArtifactValidator:
    """
    Performs structural and invariant validation on Artifact objects.
    """

    @staticmethod
    def validate(artifact: ArtifactSchema) -> None:
        logger.info("Validating artifact", extra={"mission": artifact.mission})

        if not artifact.role:
            raise ValueError("Artifact role is required")

        if not artifact.purpose:
            raise ValueError("Artifact purpose is required")


        if not artifact.mission:
            raise ValueError("Artifact mission is required")

        if not artifact.session_id:
            raise ValueError("Artifact session_id is required")

        seen_ids = set()
        for task in artifact.current_plan:
            if task.id in seen_ids:
                raise ValueError(f"Duplicate task detected: {task.id}")
            seen_ids.add(task.id)

        logger.info(
            "Artifact validation passed",
            extra={"tasks": len(artifact.current_plan)}
        )


# -------------------------------------------------------------------------
# Artifact Diff
# -------------------------------------------------------------------------

class ArtifactDiff:
    """
    Computes deterministic diffs between two Artifact objects.
    """

    @staticmethod
    def diff(old: ArtifactSchema, new: ArtifactSchema) -> Dict[str, Any]:
        logger.info("Computing artifact diff", extra={"mission": new.mission})

        diff: Dict[str, Any] = {
            "metadata_changes": {},
            "plan_changes": {
                "added": [],
                "removed": [],
                "status_changed": []
            }
        }

        for field in ["role", "purpose", "mission", "status", "current_stage"]:
            if getattr(old, field) != getattr(new, field):
                diff["metadata_changes"][field] = {
                    "from": getattr(old, field),
                    "to": getattr(new, field)
                }

        old_tasks = {t.id: t for t in old.current_plan}
        new_tasks = {t.id: t for t in new.current_plan}

        for tid, task in new_tasks.items():
            if tid not in old_tasks:
                diff["plan_changes"]["added"].append(task.description)
            elif old_tasks[tid].status != task.status:
                diff["plan_changes"]["status_changed"].append(task.description)

        for tid, task in old_tasks.items():
            if tid not in new_tasks:
                diff["plan_changes"]["removed"].append(task.description)

        return diff


# -------------------------------------------------------------------------
# Artifact Ledger
# -------------------------------------------------------------------------

class ArtifactLedger:
    """
    Maintains an append-only, hash-linked history of artifact states.
    """

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        logger.info("ArtifactLedger initialized")

    def append(self, artifact: ArtifactSchema, diff: Dict[str, Any], actor: str) -> None:
        previous_hash = (
            self._entries[-1]["entry_hash"]
            if self._entries else None
        )

        entry = {
            "mission": artifact.mission,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": actor,
            "artifact_snapshot": artifact.dict(),
            "diff": diff,
            "previous_hash": previous_hash
        }

        entry_hash = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode("utf-8")
        ).hexdigest()

        entry["entry_hash"] = entry_hash
        self._entries.append(entry)

        logger.info(
            "Artifact ledger entry appended",
            extra={"entry_hash": entry_hash[:12]}
        )

    def history(self) -> List[Dict[str, Any]]:
        return self._entries
