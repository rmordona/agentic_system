"""
StageManager loads and validates stage definitions for a workspace.

It defines stage ordering, allowed agents, and exit conditions used by
the StageGraph during execution.

StageManager does NOT execute agents or manage state.
"""
from __future__ import annotations
from core.paths import WORKSPACES_ROOT

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from events.event_bus import EventBus
from pydantic import BaseModel, Field

from llm.model_manager import ModelManager
from runtime.pipeline.pipeline_adapter import PipelineAdapter
from runtime.policy_registry import PolicyRegistry

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

####################################################################################################
# STAGE SCHEMA (STATIC CONTRACT)
#
# Purpose:
#   Defines the immutable, declarative contract for a pipeline stage.
#   This schema represents *what a stage is*, not how it is executed.
#
# Role in the System:
#   - Acts as a governance and control-plane definition.
#   - Drives orchestration decisions made by the PlanArchitect.
#   - Constrains agent behavior, stage transitions, and termination rules.
#   - Serves as a stable interface between declarative stage definitions
#     (JSON/YAML) and runtime orchestration logic.
#
# Core Properties:
#   - name:
#       Unique identifier of the stage within the workflow graph.
#
#   - description:
#       Human-readable intent and constraints of the stage.
#
#   - allowed_agents:
#       Explicit allowlist of agents permitted to act in this stage.
#       Used for enforcement and auditability.
#
#   - next_stages:
#       Declarative transition map defining which stages may follow,
#       evaluated conditionally by the PlanArchitect.
#
#   - priority:
#       Optional arbitration hint when multiple stages are eligible.
#
#   - terminal:
#       Indicates whether this stage represents an end-state of execution.
#
#   - exit_condition:
#       Predicate expression or callable evaluated against runtime state
#       to determine whether the stage may be exited.
#
# Design Principles:
#   - Static and side-effect free: contains no execution logic.
#   - Serializable and auditable: suitable for versioning and policy review.
#   - Runtime-agnostic: independent of agents, models, or execution engines.
#
# Enforcement:
#   - Interpreted and enforced by orchestration components
#     (e.g. StageManager, PlanArchitect).
#
# ------------------------------------------------------------------------------------------------
#    {
#      "name": "spec_check",
#      "description": "Ensure spec.md exists, is readable, and internally consistent. No mutations allowed.",
#      "allowed_agents": [
#        "SpecInspectorAgent"
#      ],
#      "exit_condition": "artifact_is_valid(artifact)",
#      "next_stages": [
#        {
#          "name": "clarification",
#          "condition": "artifact_has_spec_gaps(artifact)"
#        },
#        {
#          "name": "ideation",
#          "condition": "artifact_is_valid(artifact)"
#        }
#      ],
#      "terminal": false
#    }
#
####################################################################################################

class StageSchema:
    def __init__(self, 
        meta: Dict[str, Any], 
        workspace_name: str,
        policy_registry: PolicyRegistry):
        self.name: str = meta["name"]
        self.description: str = meta["description"]
        self.allowed_agents: List[str] = meta.get("allowed_agents", [])
        self.next_stages: List[str] = meta.get("next_stages", [])
        self.priority: int = meta.get("priority", 1)
        self.terminal: bool = meta.get("terminal", False)
        self.policy_registry = policy_registry
        # Exit condition can be a string expression or callable
        self.exit_condition = meta.get("exit_condition", "False")

        logger.info(f"Registering exit condition for stage '{self.name}': {type(self.exit_condition)}")
        
        if self.exit_condition:
            self.exit_condition_ast = self.policy_registry.compile(expr=self.exit_condition)
        else:
            self.exit_condition_ast = None

    def should_exit(self, state: dict) -> bool:
        try:
     
            expr = self.exit_condition_ast 
            should_exit = self.policy_registry.evaluate(expr, artifact)

            '''
            logger.info(f"State: {state}")
            condition_name = self.exit_condition.get("co_names")[0]
            logger.info(f"Should Exit: {condition_name}")
            condition_fn = self.condition_register(condition_name)
            return bool(condition_fn(artifact, state))
            '''
            return should_exit

        except Exception as e:
            logger.error(f"Error evaluating exit_condition for stage '{self.name}': {e}")
            return False

    def artifact_is_valid(self, state: dict):
        logger.info("Artifact is valid function ...")

    '''
    def __repr__(self) -> str:
        return f"Stage(name={self.name}, allowed_agents={self.allowed_agents})"
    '''

class StageManager:

    pipeline_adapter: PipelineAdapter = None

    def __init__(self, workspace_name: str):

        self.workspace_path = WORKSPACES_ROOT / workspace_name
        self.workspace_name = workspace_name
        self.entry_stage = ""

        self._stages: Dict[str, StageSchema] = {}
        self._allowed_agents: List[str] = []

        self._order: List[str] = []

        self.policy_registry: PolicyRegistry = None

    def load_pipeline_stages(self):
        # Instantiate the PipelineAdapter
        self.pipeline_adapter = PipelineAdapter(
            template_md="pipeline_template.md",
            state_log="pipeline_state.json",
            artifact_md="artifact.md",
            audit_log="artifact_audit.json",
            workspace_path=self.workspace_path,
            #model_manager=self.model_manager,
        )

    def register_stages(self):

        data = { "stages" : []}

        logger.info(f"Register Stage Policies")
        self.policy_registry = PolicyRegistry(self.workspace_path)

        logger.info(f"Hydrating Pipelines")
        self.load_pipeline_stages()
        data = self.pipeline_adapter.pipeline   

        stages_meta = data.get("stages", [])
        if not stages_meta:
            logger.warning("No stages defined in pipeline_template.md")

        # Sort by priority
        sorted_stages = sorted(stages_meta, key=lambda s: s.get("priority", 1))
        for stage_meta in sorted_stages:

            # Instantiating the Stage
            stage = StageSchema(stage_meta, self.workspace_name, self.policy_registry)

            logger.info(f"Stage Schema: {stage_meta}")
            logger.info(f"Stage's Next Stages: {stage.next_stages}")

            # Adding the stage to our list of stages
            self._stages[stage.name] = stage
            self._order.append(stage.name)

            logger.info(f"Registered stage '{stage.name}' with allowed_agents={stage.allowed_agents}")

            for agent in stage.allowed_agents:
                self._allowed_agents.append(agent)

        self.entry_stage = data.get("entry_stage")

        logger.info(f"Stages registered: {self.list_stages()}")
        logger.info(f"Prospect Agents: {self.all_allowed_agents()}")

    def get_policy(self):
        return self.policy_registry

    # -----------------------------
    # Accessors
    # -----------------------------    
    def get(self, stage_name: str) -> Optional[Stage]:
        return self._stages.get(stage_name)

    def get_description(self, stage_name: str) -> Optional[Stage]:
        return self._stages.get(stage_name)

    def get_entry_stage(self):
        return self.entry_stage

    def list_stages(self) -> List[str]:
        return list(self._stages.keys())

    def first_stage(self) -> str:
        if not self._order:
            raise ValueError("No stages loaded")
        return self._order[0]

    def next_stage(self, current_stage: str) -> Optional[str]:
        if current_stage not in self._order:
            logger.warning(f"Current stage '{current_stage}' not found in stage order")
            return None
        idx = self._order.index(current_stage)
        if idx + 1 < len(self._order):
            return self._order[idx + 1]
        return None

    def allowed_agents(self, stage_name: str) -> List[str]:
        stage = self.get(stage_name)
        return stage.allowed_agents if stage else []

    def all_allowed_agents(self) -> List[str]:
        return  self._allowed_agents if self._allowed_agents else []

    def is_terminal(self, stage_name: str) -> bool:
        stage = self.get(stage_name)
        return stage.terminal if stage else False

    def compile_predicate(self, exit_condition: dict):
        compiled_condition = self.policy_registry.compile(exit_condition)
        logger.info(f"[AgentPlanner] Exit condition '{exit_condition}' and compiled: '{compiled_condition}'")     
        return compiled_condition

    def evaluate_predicate(self, compiled_condition: dict, state_ctx: dict, artifact: dict):
        exit_result = self.policy_registry.evaluate(
            compiled_expr=compiled_condition,
            artifact=artifact,
            state_ctx=state_ctx,
        )    
        return exit_result