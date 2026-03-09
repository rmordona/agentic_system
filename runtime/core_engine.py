from __future__ import annotations
from core.paths import RUNTIME_ROOT, WORKSPACES_ROOT, GLOBAL_CONFIG_PATH, TEMPLATE_ROOT

import re
import json
from datetime import datetime, UTC, timezone
from langgraph.graph import StateGraph, END

from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Union, Optional


from langgraph.checkpoint.memory import MemorySaver

from llm.model_manager import ModelManager
from runtime.stage_manager import StageManager
from runtime.agent_manager import AgentManager

from runtime.domain_manager import SystemContext
from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import AgentContext, ArtifactSchema
from runtime.engine.domain.task import Task, HITLState

# LangGraph Nodes
from runtime.engine.nodes.validator_node import AgentValidator
from runtime.engine.nodes.runner_node import AgentRunner
from runtime.engine.nodes.planner_node import AgentPlanner 
from runtime.engine.nodes.hitl_node import AgentHITL
from runtime.engine.nodes.refiner_node import AgentIntentRefiner
from runtime.engine.nodes.classifier_node import AgentClassifier
from runtime.engine.nodes.governance_node import AgentGovernance
from runtime.engine.nodes.domain_node import AgentDomain

#Logger
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")


##################################################################
# THE TRI-PLANE ARCHITECTURE
# -------------------------
# Purpose:
#   The Tri-Plane Architecture defines a strict separation of concerns between
#   control, execution, and data in an agentic system.
#
#   It ensures that reasoning, action, and evidence are isolated, auditable,
#   and composable — enabling safe multi-agent collaboration and replay.
#
# Mental Model:
#   Think of execution as a continuous cycle:
#
#     Artifact (Control) → Agent (Decision) → Tool (Execution) → Data (Evidence)
#
#   - The Artifact dictates intent, constraints, and progress.
#   - The Agent reasons and decides what action to take next.
#   - The Tool performs the concrete action.
#   - The Data records the outcome of that action.
#
#   Each plane evolves independently but remains causally linked.
#
# ----------------------------------------------------------------
# Plane Definitions
#
# Control Plane (control_raw):
#   - Canonical source of truth for intent and workflow state.
#   - Human-readable and agent-readable.
#   - Governs what *should* happen.
#
#   Key Question:
#     "Is the task 'Book Flight' checked off yet?"
#
# Execution Plane (tool_raw):
#   - Immutable record of concrete actions taken.
#   - Captures tool invocations, parameters, and execution results.
#   - Governs what *was done*.
#
#   Key Question:
#     "What API parameters did we send to Delta at 2 PM?"
#
# Data Plane (data_raw):
#   - Immutable record of domain-specific outcomes and evidence.
#   - Stores business-level results derived from execution.
#   - Governs what *was produced*.
#
#   Key Question:
#     "What is the final confirmation number for the user?"
#
# ----------------------------------------------------------------
# Architectural Guarantees:
#   - No plane may directly mutate another plane.
#   - Control logic MUST NOT depend on tool or data internals.
#   - All planes are append-only for auditability.
#   - Replay and forensic reconstruction are always possible.
#
# In short:
#   Control decides.
#   Execution acts.
#   Data proves.
##################################################################
# -----------------------------------------------------------------------------
# CoreEngine
# -----------------------------------------------------------------------------
# Orchestration assembly for the Agentic Operating System.
#
# CoreEngine:
#   - Initializes system context, stages, tools, and models
#   - Instantiates the execution (AgentRunner) and control (AgentPlanner) nodes
#   - Wires them into a cyclic LangGraph state machine
#   - Enforces termination, safety, and human-in-the-loop interrupts
#
# This component is the system governor:
#   it defines how intelligence flows, but does not perform
#   reasoning or execution itself.
# -----------------------------------------------------------------------------
# In terms of the Architecture. We will follow this route
#
#    User Intent
#        ↓
#    IntentRefiner → structured_intent / normalized_intent
#        ↓
#    AgentClassifier → decide agent profile / capability
#        ↓
#    AgentGovernance → pipeline stage, allowed agents, HITL flags
#        ↓
#    AgentPlanner → generate tasks per agent
#        ↓
#    AgentRunner → execute tasks
#        ↓
#    AgentGovernance → next stage (loop)
# -----------------------------------------------------------------------------
class CoreEngine:
    """
    The Orchestration Assembly for the Agnostic OS.
    Wires together the AgentRunner (Execution) and AgentPlanner (Control).
    """
    def __init__(
        self, 
        workspace_name: str,
        workspace_meta: dict,
    ):
        self.workspace_path = WORKSPACES_ROOT / workspace_name
        self.workspace_name = workspace_name

        self.domain = workspace_meta.get("domain")

        self.template_repo = TEMPLATE_ROOT

        self.session_id = None
        self.user_intent = None
        self.compiled_graph = None
        

    # ------------------------------------------------------------------
    # Initialized from runtime_manager.py at bootstrap
    # ------------------------------------------------------------------
    async def initialize(self):

        # --------------------------------------------------
        # 1. Stage Management
        # --------------------------------------------------
        # logger.info("Initializing Stage Manager")
        # self.stage_manager = StageManager(workspace_name=self.workspace_name)
        # self.stage_manager.register_stages()
        # logger.info("Stage Manager initialized")

        # --------------------------------------------------
        # 2. Agent Management
        # --------------------------------------------------
        #logger.info("Initializing Agent Manager")
        #self.agent_manager = AgentManager(workspace_name=self.workspace_name)
        #self.agent_manager.scan_and_register_agents()
        #logger.info("Agent Manager initialized")

        # --------------------------------------------------
        # 3. System Context
        # --------------------------------------------------
        self.context = SystemContext()

        # --------------------------------------------------
        # 4. Initial Data Raw Setup 
        # --------------------------------------------------
        # Now based on agent
        #self.initial_data_envelope = self.context.data_manager.get_initial_envelope(domain)

        # --------------------------------------------------
        # 5. LLM Models
        # --------------------------------------------------
        logger.info("Initializing LLM models")
        self.agent_llm = ModelManager.spin_model()
        self.architect_llm = ModelManager.spin_model()
        self.core_llm = ModelManager.spin_model()
        self.refiner_llm = ModelManager.spin_model()

        # --------------------------------------------------
        # 6. Engine Hemispheres
        # --------------------------------------------------
        #    Planner → creates intent
        #    Runner → executes tools
        #    Validator → enforces truth
        #    PredicateEngine → is the law
        #    _should_continue → just checks the verdict

        logger.info("Initializing Agent Nodes")
        self.refiner      = AgentIntentRefiner(self.refiner_llm)
        self.classifier   = AgentClassifier(self.refiner_llm)
        self.domainnode   = AgentDomain(self.context)
        self.governance   = AgentGovernance(self.context)
        self.planner      = AgentPlanner(self.context, self.architect_llm)
        self.runner       = AgentRunner(self.context, self.agent_llm)
        self.validator    = AgentValidator()
        self.hitl         = AgentHITL(self.context, True, 10, True )
        logger.info("Core Engine initialized successfully")

    # --------------------------------------------------
    # Shutdown MCP sessions when done.
    # --------------------------------------------------
    async def shutdown(self):
        """Cleanly close all persistent MCP sessions."""
        await self.context.tool_manager.shutdown()

    # --------------------------------------------------
    # Graph Compilation invoked from orchestrator.py
    # --------------------------------------------------
    def compile(self):
        """
        Wires the nodes into a persistent cyclic state machine.
        """
        workflow = StateGraph(StateSchema)

        # Register the Hemispheres
        workflow.add_node("refiner", self.refiner)
        workflow.add_node("classifier", self.classifier)
        workflow.add_node("domain", self.domainnode)
        workflow.add_node("governance", self.governance)
        workflow.add_node("planner", self.planner)
        workflow.add_node("runner", self.runner)
        workflow.add_node("validator", self.validator)
        workflow.add_node("hitl", self.hitl)
        
        workflow.add_edge("classifier", "domain")
        workflow.add_edge("domain", "governance")
        workflow.add_edge("governance", "planner")
        workflow.add_edge("planner", "runner")
        workflow.add_edge("runner", "validator")

        # The Planner's output determines the next step
        workflow.add_conditional_edges("planner", self.planner._should_continue )

        # Define the entry point to the Logical Flow
        workflow.set_entry_point("refiner")

        # Decide whether we require HITL or routes to the default planner
        workflow.add_conditional_edges(
            "validator",
            self.validator.route_after_validation,
            {
                "Route_To_HITL": "hitl",
                "Route_To_Refiner": "refiner"
            }
        )

        # Decide whether we require classification (During bootstrapping/context switching) 
        # at start of conversation or new session / new thread.
        workflow.add_conditional_edges("refiner", 
            self.refiner.route_after_refining,
            {
                "Route_To_HITL" : "hitl",
                "Route_To_Classifier": "classifier",
                "Route_To_Governance": "governance",
            }
        )

        # required such that after HITL, we can resume from where we are interrupted. see core_engine.py (AgentHITL)
        # Rse a 'breakpoint' on the planner node if a human tool was called
        checkpointer = MemorySaver()
        self.compiled_graph = workflow.compile(checkpointer=checkpointer)

        return self.compiled_graph
        #return workflow.compile(interrupt_before=["agent"] if self._check_hitl_needed else [])

    # -----------------------------------------------------
    # Instantiate a new State, invoked from orchestrator.py
    # ------------------------------------------------------
    async def acquire_new_state(self, user_intent: str, session_id: str, thread_id: str):

        # 1. Initialize empty state (storage-safe only fields)
        state = StateSchema(
            session_id=session_id,
            thread_id=thread_id,
            domain=self.domain,
            original_intent=user_intent,
            workflow_metadata={
                "status": "running",
                "initial_timestamp": datetime.now(UTC).isoformat(),
            },
        )

        # 3. No active agent yet (planner chooses)
        # state.active_agent remains None
        # state.agents remains {}

        return state

    # --------------------------------------------------
    # HITL detection
    # --------------------------------------------------
    def _check_hitl_needed(self, state: "StateSchema") -> bool:
        """
        Determines if last tool execution requires human intervention.
        """
        agent_ctx = state.agentContext[state.agent]

        if not agent_ctx.tool_raw: 
            return False
        last_tool = list(agent_ctx.tool_raw.values())[-1][-1]  # last tool envelope
        last_env = ToolEnvelope.model_validate_json(last_tool)
        pending = last_env.output and last_env.output.get("status") == "PENDING_HUMAN"
        if pending:
            logger.info(f"[CoreEngine] HITL required for tool '{last_env.tool_name}' at stage '{last_env.stage}'")
        return pending

    def _extract_tasks(self, raw_llm_text: str) -> str:
        """
        Filters the LLM response to include ONLY lines starting with '- [ ]'.
        """
        # Regex explanation: 
        # ^: Start of line
        # - \[ \]: Matches the literal characters '- [ ]'
        # .*: Matches everything else on that line
        task_pattern = r"^- \[ \].*"
        
        # We use re.MULTILINE to check every line in the string
        tasks = re.findall(task_pattern, raw_llm_text, re.MULTILINE)
        
        # Join them back into a single string for the template
        return "\n".join(tasks)


