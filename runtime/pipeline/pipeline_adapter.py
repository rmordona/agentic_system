# -----------------------------------------------------------------------------
# Project: Agentic System
# File: pipeline/pipeline_adapter.py
#
# Description:
#
#   PipelineAdapter is the control-plane bridge between human-authored pipeline
#   definitions and runtime agent execution. It governs how multi-agent workflows
#   are validated, evolved, executed, audited, and persisted — without coupling
#   governance logic to execution engines.
#
#   Responsibilities:
#     - Load and parse pipeline_template.md (human-readable DSL)
#     - Extract machine-readable pipeline structure via LLM
#     - Perform static validation (linting) and governance checks
#     - Perform semantic diffing and risk assessment across pipeline versions
#     - Adapt symbolic pipeline definitions into runtime routing logic
#     - Track pipeline execution state across stages and iterations
#     - Evaluate exit conditions and dynamic routing decisions
#     - Persist execution artifacts and audit trails via Markdown adapters
#
#   This module explicitly separates:
#     - Control Plane (pipeline definition, governance, safety)
#     - Execution Plane (LangGraph / agent runtime)
#     - State & Truth Plane (artifact.md, audit logs)
#
#
# High-Level Flow:
#
#   pipeline_template.md                     # human-authored pipeline DSL
#           ↓
#   PipelineTemplateExtractor.extract()      # Markdown → structured JSON
#           ↓
#   PipelineLinter.lint()                    # static validation & governance
#           ↓
#   PipelineDiff.diff()                      # semantic diff & risk assessment
#           ↓
#   PipelineAdapter (state + routing logic)  # prepares runtime decisions
#           ↓
#   StageGraph / LangGraph                   # executes agent stages
#           ↓
#   Agents emit structured outputs           # stage-scoped, append-only
#           ↓
#   PipelineAdapter.process_stage_outputs()  # merge + persist outputs
#           ↓
#   SDDAgentMarkdownAdapter                  # artifact evolution + audit
#           ↓
#   artifact.md  +  artifact_audit.json      # authoritative state & traceability
#
#
# Execution Model:
#
#   Orchestrator drives execution via LangGraph:
#
#     async for event in graph.astream(state):
#         emit(event)
#
#   Routing decisions and exit conditions are evaluated through callbacks
#   registered by PipelineAdapter — LangGraph remains execution-only and
#   unaware of governance, linting, or artifact persistence.
#
#
# Design Principles:
#   - Human-readable pipelines, machine-enforced execution
#   - Fail-fast on structural and governance violations
#   - Immutable audit trails for compliance and replay
#   - Deterministic routing with explicit exit semantics
#   - Decoupled agents with zero filesystem or routing authority
#
##################################################################################
# Artifact Semantics in Agentic Pipelines
# --------------------------------------
#
# The "artifact" is the canonical, shared state object of an agentic pipeline.
# It represents everything the system has produced, observed, or decided so far,
# and it is the ONLY object stages are allowed to read from or write to, subject
# to explicit governance rules.
#
# In modern agentic systems, an artifact is:
#   - A structured data object (not free-form text)
#   - Versioned and auditable
#   - Deterministic and replayable
#   - The single source of truth for pipeline state
#
# The artifact is NOT:
#   - A single file
#   - A single proposal
#   - A single agent output
#
# The artifact IS:
#   - The source of truth
#   - The decision substrate for routing and validation
#   - The input to the pipeline execution graph
#
# All exit conditions and routing rules operate exclusively on the artifact.
# For example:
#
#   Exit Condition: all_proposals_reviewed(artifact)
#
# This means:
#   "Given the current pipeline state as recorded in the artifact,
#    have all proposals been evaluated?"
#
# The pipeline NEVER asks the LLM subjective questions like:
#   "Did you review everything?"
#
# Instead, it asks objective, state-based questions:
#   "What does the artifact objectively show?"
#
# This design enables:
#   - Deterministic execution
#   - Full auditability
#   - Reliable replay and simulation
#   - Strong governance and safety guarantees
#
# Example of  Artifacts
#    artifact = {
#        "spec": {...},                      # parsed spec.md
#        "proposals": [...],                 # ideation outputs
#        "reviews": [...],                   # critic feedback
#        "accepted_proposals": [...],        # synthesis result
#        "rejected_proposals": [...],
#        "issues": [...],                    # detected problems
#        "metadata": {
#            "stage_history": [...],
#            "timestamps": {...},
#            "agents_used": {...},
#        }
#    }
#
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

import json
import yaml
from datetime import datetime
from typing import List, Dict, Optional, Any
import os

from llm.model_manager import ModelManager
# from runtime.sdd_pipeline_template_extractor import PipelineTemplateExtractor
from runtime.pipeline.pipeline_extractor import PipelineExtractor
from runtime.pipeline.sdd_agent_markdown_adapter import SDDAgentMarkdownAdapter
from runtime.pipeline.pipeline_linter import PipelineLinter, PipelineLintError
from runtime.pipeline.pipeline_diff import PipelineDiff


class PipelineAdapter:
    def __init__(
        self,
        template_md: str = "pipeline_template.md",
        state_log: str = "pipeline_state.json",
        artifact_md: str = "artifact.md",
        audit_log: str = "artifact_audit.json",
        workspace_path : str = None,
        model_manager : ModelManager = None,
        previous_pipeline_path: Optional[str] = None,
        fail_on_lint_error: bool = True
    ):
        """
        Initialize the adapter:
        - Load pipeline template
        - Lint pipeline
        - Diff against previous version (optional)
        - Validate structure
        - Load pipeline state
        - Initialize markdown artifact handler
        """

        logger.info(f"Workspace Path: {workspace_path}")

        self.workspace_path = workspace_path
        self.template_path = workspace_path / "templates" / template_md
        self.state_path = workspace_path / "state" / state_log
        self.artifact_path =  workspace_path / "artifacts" / artifact_md
        self.audit_path = workspace_path / "audit" / audit_log

        self.previous_pipeline_path = previous_pipeline_path

        logger.info(
            "Initializing PipelineAdapter | "
            f"template_path={self.template_path}, state_path={self.state_path}"
        )

        logger.info(
            "Initializing PipelineAdapter | "
            f"state_path_path={self.state_path}, audit_path={self.audit_path}"
        )

        # LLM Model Manager
        self.model_manager = model_manager

        # 1️⃣ Load pipeline template
        self.pipeline = self._load_pipeline_template(workspace_path)

        # 2️⃣ Lint pipeline
        self._lint_pipeline(fail_on_lint_error)

        # 3️⃣ Diff pipeline if previous exists
        if previous_pipeline_path and os.path.exists(previous_pipeline_path):
            self._diff_pipeline(previous_pipeline_path)

        # 4️⃣ Validate minimal structure
        self._validate_pipeline()

        # 5️⃣ Load state
        self.state = self._load_state()

        # 6️⃣ Initialize SDDAgentMarkdownAdapter
        self.md_adapter = SDDAgentMarkdownAdapter(
            md_path=self.artifact_path,
            audit_path=self.audit_path
        )

        logger.info("PipelineAdapter initialized successfully")

    ###########################
    # Internal helpers
    ###########################

    def _lint_pipeline(self, fail_on_error: bool):
        logger.info("Linting pipeline definition")
        # logger.info(f"Pipeline: {self.pipeline}")
        linter = PipelineLinter(self.pipeline)
        result = linter.lint(fail_fast=fail_on_error)

        if not result["is_valid"]:
            logger.error(
                "Pipeline lint errors detected",
                extra={"errors": result["errors"]}
            )

        if result["warnings"]:
            logger.warning(
                "Pipeline lint warnings detected",
                extra={"warnings": result["warnings"]}
            )

        logger.info("Pipeline linting completed")

    def _diff_pipeline(self, previous_pipeline_path: str):
        logger.info(
            "Diffing pipeline against previous version | "
            f"path={previous_pipeline_path}"
        )

        with open(previous_pipeline_path, 'r') as f:
            prev_pipeline = yaml.safe_load(f)

        diff_tool = PipelineDiff(
            old_pipeline=prev_pipeline,
            new_pipeline=self.pipeline
        )
        diff_result = diff_tool.diff()

        if diff_result["risk_assessment"]:
            logger.warning(
                "Pipeline diff risk assessment detected",
                extra={"risk": diff_result["risk_assessment"]}
            )

        if diff_result["requires_hitl"]:
            logger.warning(
                "Pipeline changes require HITL approval"
            )

        logger.info("Pipeline diffing completed")


    def _load_pipeline_template(self, workspace_path: str) -> Dict[str, Any]:
        logger.info(
            "Loading pipeline template | "
            f"path={self.template_path}"
        )

        if not os.path.exists(self.template_path):
            logger.error("Pipeline template not found")
            raise FileNotFoundError(
                f"Pipeline template not found: {self.template_path}"
            )

        with open(self.template_path, 'r') as f:
            content = f.read()

        # Case 1: YAML block inside Markdown
        if '```yaml' in content:
            logger.debug("Detected YAML block inside Markdown template")
            try:
                yaml_block = content.split('```yaml')[1].split('```')[0]
                parsed = yaml.safe_load(yaml_block)
                logger.info("Pipeline template parsed from YAML block")
                return parsed
            except Exception as e:
                logger.exception("Failed to parse YAML block from Markdown")
                raise ValueError(f"Failed to parse YAML block: {e}")

        # Case 2: Pure YAML
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict) and "stages" in parsed:
                logger.info("Pipeline template parsed as pure YAML")
                return parsed
        except Exception:
            logger.debug("Content is not valid pure YAML")

        # Case 3: Markdown → LLM extraction
        logger.info("Falling back to Markdown → LLM pipeline extraction")
        return self._extract_pipeline_from_markdown(workspace_path)

    def _extract_pipeline_from_markdown(self, workspace_path: str) -> Dict[str, Any]:
        logger.info("Extracting pipeline using Mistune 3.0 parser rom Markdown")    
        parser = PipelineExtractor(self.workspace_path)
        pipeline = parser.parse()

        try:
            extracted_stages = json.dumps(pipeline, indent=2)
            logger.info( f"[PipelineExtractor] JSON parsing successful")
            logger.info(f"Extracted stages: {extracted_stages}")
            return json.loads(extracted_stages)

        except json.JSONDecodeError as e:
            logger.error(f"[PipelineExtractor:] Invalid JSON returned from LLM")
            raise ValueError(f"[PipelineTemplateExtractor:] ")
                
        logger.info(f"Extracted the stage..")
        return {}

    '''
    def _extract_pipeline_from_markdown(self, markdown: str) -> Dict[str, Any]:
        logger.info("Extracting pipeline via LLM from Markdown")       
        extractor = PipelineTemplateExtractor(llm_client=self.model_manager, workspace_path=self.workspace_path )
        return extractor.extract(markdown)
    '''

    def _validate_pipeline(self):
        logger.info("Validating pipeline structure")

        if "stages" not in self.pipeline:
            logger.error("Pipeline missing 'stages' list")
            raise ValueError("Pipeline must contain a 'stages' list.")

        for stage in self.pipeline["stages"]:
            if "name" not in stage:
                logger.error("Pipeline stage missing name")
                raise ValueError("Each stage must have a name.")

        logger.info(
            "Pipeline structure validated | "
            f"stages={len(self.pipeline['stages'])}"
        )

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            logger.info(
                "Loading existing pipeline state | "
                f"path={self.state_path}"
            )
            with open(self.state_path, 'r') as f:
                return json.load(f)

        logger.info("Initializing new pipeline state")
        return {
            "current_stage": None,
            "iterations": {},
            "stage_history": [],
            "hitl_approved": False
        }

    ###########################
    # Public methods
    ###########################

    def get_current_stage(self) -> Optional[str]:
        return self.state.get("current_stage")

    def evaluate_exit_condition(self, artifact: Dict[str, Any]) -> bool:
        stage_name = self.get_current_stage()
        if not stage_name:
            logger.debug("No current stage set; exit condition false")
            return False

        stage_def = self._get_stage_def(stage_name)
        if not stage_def or "exit_condition" not in stage_def:
            logger.debug("No exit condition defined; defaulting to True")
            return True

        condition = stage_def["exit_condition"]
        local_ctx = self._build_eval_context(artifact)

        try:
            result = bool(eval(condition, {"__builtins__": {}}, local_ctx))
            logger.debug(
                "Exit condition evaluated",
                extra={"stage": stage_name, "result": result}
            )
            return result
        except Exception as e:
            logger.warning(
                "Failed to evaluate exit condition",
                extra={"stage": stage_name, "error": str(e)}
            )
            return False

    def get_next_stage(
        self,
        artifact: Dict[str, Any],
        hitl_signal: bool = False
    ) -> Dict[str, Any]:
        if hitl_signal:
            self.state["hitl_approved"] = True
            logger.info("HITL approval signal received")

        current_stage = self.get_current_stage()

        if not current_stage:
            next_stage_def = self.pipeline["stages"][0]
            self.state["current_stage"] = next_stage_def["name"]
            self._log_stage_transition(
                next_stage_def["name"],
                reason="Pipeline start"
            )
            return self._build_routing_decision(next_stage_def)

        exit_ok = self.evaluate_exit_condition(artifact)
        if not exit_ok:
            logger.info(
                "Exit condition not met; staying in stage",
                extra={"stage": current_stage}
            )
            return self._build_routing_decision(
                self._get_stage_def(current_stage),
                reason="Exit condition not met"
            )

        stage_def = self._get_stage_def(current_stage)
        next_stages = stage_def.get("next_stages", [])

        if not next_stages:
            logger.info("Terminal stage reached")
            return self._build_routing_decision(
                stage_def,
                reason="Terminal stage",
                hitl_required=hitl_signal
            )

        for candidate in next_stages:
            candidate_name = (
                candidate["name"] if isinstance(candidate, dict) else candidate
            )
            candidate_def = self._get_stage_def(candidate_name)
            if not candidate_def:
                continue

            condition = candidate.get("condition") if isinstance(candidate, dict) else None
            if condition:
                try:
                    if not eval(
                        condition,
                        {"__builtins__": {}},
                        self._build_eval_context(artifact)
                    ):
                        continue
                except Exception as e:
                    logger.warning(
                        "Failed to evaluate routing condition",
                        extra={"condition": condition, "error": str(e)}
                    )
                    continue

            self.state["current_stage"] = candidate_def["name"]
            self._log_stage_transition(
                candidate_def["name"],
                reason=f"Dynamic routing from '{current_stage}'"
            )
            return self._build_routing_decision(
                candidate_def,
                hitl_required=hitl_signal
            )

        logger.warning("No valid next stage found; remaining in current stage")
        return self._build_routing_decision(
            stage_def,
            reason="No valid next stage found"
        )

    def process_stage_outputs(
        self,
        stage_name: str,
        agent_outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        logger.info(
            "Processing stage outputs",
            extra={"stage": stage_name, "outputs": len(agent_outputs)}
        )

        self.update_stage_state(stage_name, agent_outputs)
        self.md_adapter.process_stage_outputs(agent_outputs)

        merged_artifact = {"current_plan": []}
        for output in agent_outputs:
            for k, v in output.items():
                if k not in ["stage", "agent_id", "timestamp"]:
                    if isinstance(v, list):
                        merged_artifact["current_plan"].extend(v)
                    else:
                        merged_artifact["current_plan"].append(v)

        return merged_artifact

    def update_stage_state(
        self,
        stage_name: str,
        agent_outputs: List[Dict[str, Any]]
    ):
        logger.debug(
            "Updating stage state",
            extra={"stage": stage_name}
        )

        if stage_name not in self.state["iterations"]:
            self.state["iterations"][stage_name] = []

        self.state["iterations"][stage_name].append({
            "timestamp": datetime.utcnow().isoformat(),
            "outputs": agent_outputs
        })

        self.state["stage_history"].append({
            "stage": stage_name,
            "timestamp": datetime.utcnow().isoformat()
        })

    def persist_state(self):
        logger.info("Persisting pipeline state")
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    ###########################
    # Internal helpers
    ###########################

    def _get_stage_def(self, stage_name: str) -> Optional[Dict[str, Any]]:
        for s in self.pipeline.get("stages", []):
            if s["name"] == stage_name:
                return s
        return None

    def _build_eval_context(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "artifact": artifact,
            "hitl_approved": self.state.get("hitl_approved", False),
            "accepted_proposals_exist": self.accepted_proposals_exist,
            "critical_issues_detected": self.critical_issues_detected,
            "all_proposals_invalid": self.all_proposals_invalid,
            "all_proposals_reviewed": self.all_proposals_reviewed,
            "artifact_has_spec_gaps": self.artifact_has_spec_gaps,
            "clarifications_resolved": self.clarifications_resolved,
            "clarification_failed": self.clarification_failed,
            "proposal_conflicts_with_spec": self.proposal_conflicts_with_spec,
            "artifact_has_conflicts": self.artifact_has_conflicts,
            "artifact_requires_new_ideas": self.artifact_requires_new_ideas,
            "artifact_is_valid": self.artifact_is_valid,
        }

    def _build_routing_decision(
        self,
        stage_def: Dict[str, Any],
        reason: str = "",
        hitl_required: bool = False
    ) -> Dict[str, Any]:
        return {
            "current_stage": self.get_current_stage(),
            "next_stage": stage_def["name"],
            "allowed_agents": stage_def.get("allowed_agents", []),
            "reason": reason,
            "hitl_required": hitl_required
        }

    def _log_stage_transition(self, stage_name: str, reason: str):
        logger.info(
            "Pipeline stage transition",
            extra={"stage": stage_name, "reason": reason}
        )

    ###########################
    # Exit Conditions
    ###########################

    def accepted_proposals_exist(self, artifact: Dict[str, Any]) -> bool:
        return any(p.get("status") == "accepted" for p in artifact.get("current_plan", []))

    def critical_issues_detected(self, artifact: Dict[str, Any]) -> bool:
        return any(p.get("conflict", False) for p in artifact.get("current_plan", []))

    def all_proposals_invalid(self, artifact: Dict[str, Any]) -> bool:
        return all(p.get("status") == "invalid" for p in artifact.get("current_plan", []))

    def all_proposals_reviewed(self, artifact: Dict[str, Any]) -> bool:
        return all("status" in p for p in artifact.get("current_plan", []))

    def artifact_has_conflicts(self, artifact: Dict[str, Any]) -> bool:
        return any(p.get("conflict", False) for p in artifact.get("current_plan", []))

    def artifact_requires_new_ideas(self, artifact: Dict[str, Any]) -> bool:
        return any(p.get("superseded", False) for p in artifact.get("current_plan", []))

    def artifact_is_valid(self, artifact: Dict[str, Any]) -> bool:
        return all(not p.get("conflict", False) for p in artifact.get("current_plan", []))

    def artifact_has_spec_gaps(self, artifact: Dict[str, Any]) -> bool:
        return artifact.get("spec_gaps", False)

    def clarifications_resolved(self, artifact: Dict[str, Any]) -> bool:
        return artifact.get("clarifications_resolved", False)

    def clarification_failed(self, artifact: Dict[str, Any]) -> bool:
        return artifact.get("clarification_failed", False)

    def proposal_conflicts_with_spec(self, artifact: Dict[str, Any]) -> bool:
        return artifact.get("conflicts_with_spec", False)
