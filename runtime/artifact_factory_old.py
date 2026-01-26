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

import re
import mistune
from typing import Dict, Any, List, Optional

from pydantic import BaseModel
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


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

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import UUID


class Task(BaseModel):
    id: str
    description: str
    stage: str
    status: Literal["pending", "done", "blocked"] = "pending"


class HITLState(BaseModel):
    required: bool = False
    approved: Optional[bool] = None
    comments: Optional[str] = None


class Artifact(BaseModel):
    # ---- Versioning ----
    schema_version: Literal["1.0"] = "1.0"

    # ---- Identity ----
    mission: str
    session_id: str
    status: Literal[
        "initialized",
        "running",
        "blocked",
        "completed",
        "aborted"
    ]

    # ---- Planning ----
    current_stage: str
    current_plan: List[Task] = Field(default_factory=list)
    plan_history: List[Dict] = Field(default_factory=list)

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
    Compiles artifact Markdown into validated ArtifactSchema objects.

    This factory:
      - Parses Markdown deterministically
      - Extracts structured planning data
      - Preserves raw content for LLM grounding

    This factory does NOT:
      - Decide ownership
      - Enforce workflow rules
      - Perform semantic judgment
    """

    def __init__(self):
        self.parser = mistune.create_markdown(renderer=None)
        logger.info("ArtifactFactory initialized")

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _parse_plan_line(self, line: str) -> Optional[PlanItem]:
        logger.debug("Parsing plan line", extra={"line": line})

        match = re.search(r"-\s*(.*?)\s*#\s*(.*)", line)
        if not match:
            return None

        task_text = match.group(1).strip()
        metadata_str = match.group(2)

        meta_parts = [p.strip() for p in metadata_str.split(",")]
        role = meta_parts[0]

        meta_dict: Dict[str, str] = {}
        for part in meta_parts[1:]:
            if ":" in part:
                k, v = part.split(":", 1)
                meta_dict[k.strip()] = v.strip()
            elif "=" in part:
                k, v = part.split("=", 1)
                meta_dict[k.strip()] = v.strip()

        return PlanItem(
            task=task_text,
            role=role,
            stage=meta_dict.get("stage", "unknown"),
            superseded=meta_dict.get("superseded", "false").lower() == "true"
        )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def compile(self, md_text: str) -> ArtifactSchema:
        """
        Compiles Markdown text directly into an ArtifactSchema.
        """
        logger.info("Compiling artifact")

        ast = self.parser(md_text)

        name = None
        role_owner = None
        purpose = None
        current_plan: List[PlanItem] = []
        history: List[Dict[str, Any]] = []

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

                    plan_item = self._parse_plan_line(line_text)
                    if plan_item:
                        current_plan.append(plan_item)

            if node["type"] == "paragraph" and not current_section:
                text = "".join(c.get("text", "") for c in node.get("children", []))

                if "Artifact:" in text:
                    name = text.split("Artifact:", 1)[1].strip()
                if "Role:" in text:
                    role_owner = text.split("Role:", 1)[1].strip()
                if "Purpose:" in text:
                    purpose = text.split("Purpose:", 1)[1].strip()

        logger.info(
            "Artifact compiled",
            extra={
                "name": name,
                "plan_items": len(current_plan)
            }
        )

        return ArtifactSchema(
            name=name,
            role_owner=role_owner,
            purpose=purpose,
            current_plan=current_plan,
            history=history,
            raw_content=md_text
        )


# -------------------------------------------------------------------------
# Artifact Validator
# -------------------------------------------------------------------------

class ArtifactValidator:
    """
    Performs structural and invariant validation on ArtifactSchema objects.

    This validator:
      - Enforces required fields
      - Detects invalid plan states
      - Ensures internal consistency

    This validator does NOT:
      - Judge correctness of plans
      - Enforce agent authority
      - Decide workflow transitions
    """

    @staticmethod
    def validate(artifact: ArtifactSchema) -> None:
        logger.info("Validating artifact", extra={"artifact": artifact.name})

        if not artifact.name:
            raise ValueError("Artifact name is required")

        if not artifact.role_owner:
            raise ValueError("Artifact role_owner is required")

        if not artifact.purpose:
            raise ValueError("Artifact purpose is required")

        active_tasks = set()
        for item in artifact.current_plan:
            if not item.superseded:
                if item.task in active_tasks:
                    raise ValueError(
                        f"Duplicate active task detected: {item.task}"
                    )
                active_tasks.add(item.task)

        logger.info(
            "Artifact validation passed",
            extra={"active_tasks": len(active_tasks)}
        )


# -------------------------------------------------------------------------
# Artifact Diff
# -------------------------------------------------------------------------

class ArtifactDiff:
    """
    Computes deterministic diffs between two ArtifactSchema objects.

    Output is structured and machine-readable for:
      - Audit trails
      - Agent reasoning
      - Governance decisions
    """

    @staticmethod
    def diff(old: ArtifactSchema, new: ArtifactSchema) -> Dict[str, Any]:
        logger.info(
            "Computing artifact diff",
            extra={"artifact": new.name}
        )

        diff: Dict[str, Any] = {
            "metadata_changes": {},
            "plan_changes": {
                "added": [],
                "removed": [],
                "superseded": []
            }
        }

        # Metadata diffs
        for field in ["name", "role_owner", "purpose"]:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                diff["metadata_changes"][field] = {
                    "from": old_val,
                    "to": new_val
                }

        # Plan diffs
        old_tasks = {p.task: p for p in old.current_plan}
        new_tasks = {p.task: p for p in new.current_plan}

        for task, item in new_tasks.items():
            if task not in old_tasks:
                diff["plan_changes"]["added"].append(task)
            elif old_tasks[task].superseded is False and item.superseded is True:
                diff["plan_changes"]["superseded"].append(task)

        for task in old_tasks:
            if task not in new_tasks:
                diff["plan_changes"]["removed"].append(task)

        logger.info(
            "Artifact diff computed",
            extra={
                "added": len(diff["plan_changes"]["added"]),
                "removed": len(diff["plan_changes"]["removed"]),
                "superseded": len(diff["plan_changes"]["superseded"])
            }
        )

        return diff


# -------------------------------------------------------------------------
# Artifact Ledger
# -------------------------------------------------------------------------

class ArtifactLedger:
    """
    Maintains an append-only, hash-linked history of artifact states.

    This ledger:
      - Preserves full artifact snapshots
      - Links entries cryptographically
      - Enables audit, replay, and rollback

    This ledger does NOT:
      - Enforce permissions
      - Decide which changes are allowed
    """

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        logger.info("ArtifactLedger initialized")

    def append(
        self,
        artifact: ArtifactSchema,
        diff: Dict[str, Any],
        actor: str
    ) -> None:
        previous_hash = (
            self._entries[-1]["entry_hash"]
            if self._entries else None
        )

        entry = {
            "artifact_name": artifact.name,
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
            extra={
                "artifact": artifact.name,
                "entry_hash": entry_hash[:12]
            }
        )

    def history(self) -> List[Dict[str, Any]]:
        return self._entries
