import re
from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from pathlib import Path

import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated, Literal, Optional
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from langgraph.graph.message import add_messages  # optional

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from runtime.artifact_factory import ArtifactFactory

from llm.model_manager import ModelManager
from runtime.stage_manager import StageSchema, StageManager
from runtime.agent_manager import AgentManager
from runtime.policy_registry import PolicyRegistry

from runtime.agent_profiler import AgentProfile

from llm.model_manager import ModelManager

from runtime.artifact_factory import ArtifactSchema
from runtime.domain_manager import DomainType, SystemContext, DataEnvelope, ToolEnvelope, DataAdapter, ToolAdapter

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


def merge_reward_dicts(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {
        k: a.get(k, 0.0) + b.get(k, 0.0)
        for k in set(a) | set(b)
    }

def set_default_channel(key: str):
    """
    Decide which channel type to use for a given state key.

    This is the SINGLE source of truth for state semantics.
    """

    # Multi-writer, fan-in safe (event-driven)
    if key in {"history", "tool_events"}:
        return TopicChannel(list)

    # Aggregation semantics (critic vs optimistic rewards)
    if key == "rewards":
        return BinaryOperatorAggregate(
            dict,
            lambda a, b: {
                k: a.get(k, 0) + b.get(k, 0)
                for k in set(a) | set(b)
            },
        )

    # Single-writer, last-write-wins (control plane)
    return LastValue(object)

# See main.py, how role is the same as the agent name
class AgentOutput(TypedDict):
    stage: str
    role: str
    output: Any

class ToolCall(TypedDict):
    agent: str
    tool: str
    args: Dict[str, Any]
    result: Any


class StateSchema(BaseModel):
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    session_id: str

    domain: str

    # ------------------------------------------------------------------
    # Control Plane (required, immutable intent)
    # ------------------------------------------------------------------
    control_raw: ArtifactSchema = None # artifact.md / plan / contract

    # ------------------------------------------------------------------
    # Data Plane (append-only, domain governed)
    # ------------------------------------------------------------------
    data_raw:  DataEnvelope[DomainType]  = None # Field(default_factory=DataEnvelope)

    # ------------------------------------------------------------------
    # Tool Plane (append-only execution records)
    # ------------------------------------------------------------------
    tool_raw: List[ToolEnvelope[DomainType]] = Field(default_factory=list)
    # ------------------------------------------------------------------
    # Orchestration Fields
    # ------------------------------------------------------------------
    user_intent: str = ""
    task: str = ""
    agent: str = ""
    stage: str = ""
    done: bool = False

    # ------------------------------------------------------------------
    # Execution History
    # ------------------------------------------------------------------
    # History: collect all agent outputs per step (note this is agent output, becomes history)
    history_agents: List[str] = Field(default_factory=list)
    executed_agents_per_stage: Dict[str, List[str]] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Workflow Metadata
    # ------------------------------------------------------------------
    workflow_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True  # allows ArtifactSchema inside


# -----------------------------------------------------------------------------
# AgentRunner
# -----------------------------------------------------------------------------
# Execution-plane node responsible for acting on the current plan.
#
# AgentRunner:
#   - Operates strictly within the active stage contract
#   - Executes LLM-driven actions using bound runtime tools
#   - Converts tool calls into ToolEnvelopes
#   - Mutates the Data Plane (data_raw) based on verified tool output
#
# This component represents the "hands" of the system:
#   it performs work, gathers evidence, and reports results,
#   but never decides stage transitions or governance.
# -----------------------------------------------------------------------------
class AgentRunner:
    def __init__(self, context: SystemContext, stage_manager: StageManager, agent_manager: AgentManager, llm: ModelManager):

        self.context = context

        self.stage_manager = stage_manager
        self.agent_manager = agent_manager

        # Bind the dynamic tools to the LLM
        # The LLM is "primed" with a menu of actions.
        self.llm = llm.bind_tools(context.get_runtime_tools())

    # Called by langgraph graph (Can also be named as run() .... if we want to ... )
    async def __call__(self, state: StateSchema):
        """The Node function for LangGraph"""

        logger.info("************* Agent Runner is being called ...")

        logger.info(f"State received: {state}")

        stage      = state.stage        # Received from AgentPlanner
        agent_name = state.agent        # Received from AgentPlanner
        task       = state.task         # Received from AgentPlanner

        stage_meta = self.stage_manager.get(stage)
        self.enforce_stage(agent_name, stage_meta)

        # 1. Get Agent Prompt
        agent_prompt = self.agent_manager.get_agent_prompt(agent_name)

        # 2. Hydrate Context
        data_adapter = self.context.data_manager.get_adapter(state.domain)
        data_envelope = state.data_raw # DataEnvelope.model_validate_json(state.data_raw)
        
        # 3. LLM Inference
        prompt = f"Plan: {state.control_raw}\nCurrent Data: {data_envelope.payload}"
        response = await self.llm.ainvoke(prompt)

        new_tool_envelopes = []
        updated_payload = data_envelope.payload.copy()

        # 4. Execution & Mapping
        if response.tool_calls:
            for tc in response.tool_calls:
                try:
                    tool_adapter = self.context.tool_manager.get_adapter(tc["name"])
                    
                    # Execute and wrap in ToolEnvelope
                    t_env = await tool_adapter.execute(
                        agent_role="executor", 
                        stage=state.stage, 
                        **tc["args"]
                    )
                    
                except Exception as e:
                    # CRASH RECOVERY: Create an error envelope manually
                    t_env = ToolEnvelope(
                        tool_name=tc["name"],
                        input=tc["args"],
                        output=None,
                        success=False,
                        error=str(e), # Capture the traceback or message
                        agent_role="executor",
                        stage=state["stage"]
                    )

                new_tool_envelopes.append(t_env.model_dump_json())

                # Update Data Plane if successful
                if t_env.success and t_env.output:
                    updated_payload.update(t_env.output)

        # 5. Final Data Envelope Packaging
        new_data_envelope = data_adapter.create_envelope(
            payload=updated_payload,
            producer="AgentRunner",
            stage=state.stage 
        )

        logger.info(f"[AgentRunner] new data envelope: {updated_payload}")

        # Partial Update,  note: graph.astream should have the stream="update"
        return {
            "data_raw": new_data_envelope,
            "tool_raw": new_tool_envelopes
        }

    def enforce_stage(self, agent_name, stage_meta: StageSchema):
        if agent_name not in stage_meta.allowed_agents:
            raise Exception(f"{agent_name} not allowed in stage {stage_meta.name}")

# -----------------------------------------------------------------------------
# AgentPlanner
# -----------------------------------------------------------------------------
# Control-plane supervisor responsible for plan reconciliation and stage flow.
#
# AgentPlanner:
#   - Evaluates stage exit conditions and advancement rules
#   - Determines the next stage based on the StageContract
#   - Reviews recent ToolEnvelopes as execution evidence
#   - Updates the Markdown control artifact (control_raw)
#
# This component represents the "mind" of the system:
#   it reasons about progress, correctness, and next steps,
#   but never executes tools or mutates the data plane directly.
# -----------------------------------------------------------------------------

INIT_TASK = "--init--"

class AgentPlanner:
    def __init__(self, context: SystemContext, stage_manager: StageManager, agent_manager: AgentManager, llm: ModelManager):

        self.context = context
        self.stage_manager = stage_manager
        self.agent_manager = agent_manager
        self.llm = llm # Usually a smarter model like GPT-4o or Gemini Pro

        self.predicates = stage_manager.get_policy()

    async def __call__(self, state: StateSchema):
        """
        The Supervisor Node function for LangGraph / Orchestrator Runtime.
        """
        logger.info("************* Agent Planner is being called ...")

        if state.task == INIT_TASK:

            logger.info("This is the first iteration ... So acquiring the first stage and first agent ...")

            # YOU NEED TO ALSO GET THE INITIAL DATA ENVELOPE since SCHEMAS are now BASED ON AGENTS

            return await self.compose_initial_task(state)

        logger.info(f"Current Stage: {state.stage}")
        stage_meta = self.stage_manager.get(state.stage)

        logger.info(f"Build runtime state context")
        state_ctx = self.build_runtime_state_context(state)

        # --------------------------------------------------
        # 1. Evaluate exit condition first
        # --------------------------------------------------
        logger.info(f"[AgentPlanner] Evaluating stage '{state.stage}'")
        if stage_meta.exit_condition:
            logger.info(f"[AgentPlanner] Evaluate exit condition '{stage_meta.exit_condition}")

            compiled_condition = self.predicates.compile(stage_meta.exit_condition)
            logger.info(f"[AgentPlanner] Exit condition '{stage_meta.exit_condition}' and compiled: '{compiled_condition}'")

            exit_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=state.control_raw.model_dump(),
                state_ctx=state_ctx,
            )
            logger.info(f"[AgentPlanner] Exit Condition result: {exit_result}")
            if not exit_result:
                logger.info(f"[AgentPlanner] Stage '{state.stage}' incomplete, remaining in stage")
                return {"control_raw": state.control_raw}  # Stay in current stage

        # --------------------------------------------------
        # 2. Determine next stage
        # --------------------------------------------------
        logger.info(f"Determine Next Stages: {stage_meta.next_stages}")
        for transition in stage_meta.next_stages:
            logger.info(f"Transition (next stage): {transition}")
            if transition.get("condition") is None:
                logger.info(f"[AgentPlanner] Transitioning to stage '{transition.get("name")}' (unconditional)")
                return self.advance(state, transition.get("name"))

            compiled_condition = self.predicates.compile(transition.get("condition"))
            condition_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=state.control_raw.model_dump(),
                state_ctx=state_ctx,
            )
            logger.info(f"[AgentPlanner] Transition '{transition.get("name")}' condition '{transition.get("condition")}' evaluated to {condition_result}")
            if condition_result:
                return self.advance(state, transition.get("name"))

        # --------------------------------------------------
        # 3. Summarize last tool executions
        # --------------------------------------------------
        last_tools = [ToolEnvelope.model_validate_json(t) for t in state.tool_raw[-5:]]  # last 5 tools
        tool_summary = "\n".join([
            f"- Tool: {t.tool_name}, Success: {t.success}, Output: {t.output or t.error}"
            for t in last_tools
        ])
        logger.debug(f"[AgentPlanner] Tool Summary:\n{tool_summary}")


        # 2. Ask LLM to update the Markdown Artifact
        prompt = f"""
        You are the System Architect. Update the Markdown checklist based on tool evidence.
        
        CURRENT PLAN:
        {state['control_raw']}
        
        EVIDENCE FROM EXECUTION PLANE:
        {tool_summary}
        
        RULES:
        - Mark tasks with [x] only if the tool output proves completion.
        - Add NEW sub-tasks if a tool error suggests a recovery step is needed.
        - Return ONLY the updated Markdown.
        """
        
        new_plan = await self.llm.ainvoke(prompt)
        
        # return {"control_raw": new_plan.content}
        return {
            "stage": "analysis",
            "agent_name": "CriticAgent",
            "task": "Stress-test the proposed architecture for scalability risks"
        }

    ###############################################################################
    # Compose Initial Task
    ################################################################################
    async def compose_initial_task(self, state: StateSchema):

        logger.info("Composint initial task ...")

        # Acquire first stage
        first_stage = self.stage_manager.get_entry_stage()

        logger.info(f"Entry Stage: {first_stage}")

        logger.info(f"Allowed Agents: {self.stage_manager.allowed_agents(first_stage)}")

        # Acquire first agent
        first_agent = self.agent_manager.first_agent(
                self.stage_manager.allowed_agents(first_stage)
            )

        # Acquire mission statement from state.control_raw.stage.description

        if first_agent is None:
            logger.info(f"No agent to handle the first task for stage '{stage}")
            raise Exception(f"No agent to handle the first task for stage '{stage}")

        logger.info(f"Domain: {state.domain}, First Stage: {first_stage}, First Agent: {first_agent}")

        logger.info("Acquire the agent profile")
        agent_profile = self.agent_manager.get_agent_profile(first_agent)

        logger.info(f"Agent's Profile: {agent_profile}")

        logger.info("Now acquiring the first task based on user intent and user profile")

        # Acquire first task
        first_task = await self._build_initial_artifact(state.user_intent, agent_profile)

                # md_text = await self._build_initial_artifact(user_intent)
        # logger.info(f"The initial Artifact: {md_text}")


        # Given the user’s goal, what is the next concrete responsibility for this agent in this stage?
        return {
            "stage" : first_stage,
            "agent" : first_agent,
            "task" : first_task,
        }

    async def _build_initial_artifact(self, user_intent: str, profile: AgentProfile) -> str:

        logger.info("[AgentPlanner] Composing the artifact using ARCHITECT_TEMPLATE.md")
        template_repo = self.context.template_repo

        if not template_repo.exists():
            logger.error(f"Workspace path '{templates_dir}' does not exist")
            raise FileNotFoundError(f"Workspace path '{templates_dir}' does not exist")

        # We load both templates
        self.architect_template = load_file(template_repo / "ARCHITECT_TEMPLATE.md")
        # self.plan_template = self.load_file(template_repo / "PLAN_TEMPLATE.md")

        # 1. Hydrate the INSTRUCTIONS (The System Prompt)
        logger.info("[AgentPlanner] Build Phase: Hydrating the system prompt.")
        system_prompt = await hydrate(self.architect_template, {
            "profile_name": profile.name,
            "profile_role" : profile.role,
            "profile_capabilities": profile.capabilities,
            "profile_task_style" : profile.task_style,
            "profile_can_execute_tools" : str(profile.can_execute_tools),
            "profile_forbidden_actions": profile.forbidden_actions,
            "profile_schema" : profile.schema,
            "user_intent" : user_intent
        })
        logger.info(f"Agent Planner initial Prompt: {system_prompt}")

        # 2. Get the RAW TASKS from the LLM
        # The LLM only sees the Instructions and the Goal.

        logger.info("LLM Model Call ...")
        raw_tasks = await _call_llm(prompt=system_prompt, user_intent=user_intent, model_manager=self.llm)
        logger.info("LLM Model Call complete ...")

        initial_artifact=raw_tasks.content

        '''
        # 3. Inject the RAW TASKS into the SHELL (The Plan Template)
        logger.info("Now Hydrating the initial artifact.")
        initial_artifact = await hydrate(self.plan_template, {
            "MISSION_NAME": user_intent,
            "GENERATED_TASKS": self._extract_tasks(raw_tasks.content),
            "STATUS": "initialized",
            "SESSION_ID" : "Placeholder_Session_id",
            "INITIAL_TIMESTAMP" : "Placeholder_time"
        })
        '''

        logger.info(f"Initial Artifact: {initial_artifact}")

        return initial_artifact

    
    def advance(
        self,
        state: StateSchema,
        next_stage: str,
    ) -> dict:
        """
        Advance the workflow to the next stage and select the first allowed agent.

        Responsibilities:
        - Update stage
        - Select the first allowed agent for the new stage
        - Reset task
        """

        logger.info(
            f"[advance] Transitioning from stage='{state.stage}' to stage='{next_stage}'"
        )

        # 1. Resolve allowed agents for next stage
        allowed_agents = self.stage_manager.allowed_agents(next_stage)
        if not allowed_agents:
            raise RuntimeError(
                f"No allowed agents registered for stage '{next_stage}'"
            )

        # 2. Select first agent deterministically
        first_agent = self.agent_manager.first_agent(allowed_agents)

        logger.info(
            f"[advance] Next stage='{next_stage}', first agent='{first_agent}'"
        )

        return {
            "stage": next_stage,
            "agent": first_agent,
            "task": None,
        }



    ###############################################################################
    # Build a context out of the state.
    #    state.data_raw         # DataEnvelope[RealestateSchema]
    #    ctx["data"]            # dict of RealestateSchema fields
    #    ctx["data_meta"]       # metadata of the data envelope
    #    ctx["recent_tools"]    # metadata of the tool envelope - last 5 tool executions as dicts
    #    ctx["current_stage"] = state.stage
    ################################################################################
    def build_runtime_state_context(self, state: StateSchema) -> dict:
        """
        Build a context dictionary from a StateSchema to evaluate stage predicates.
        """
        # Basic State context
        logger.info("Building predicate state context ...")
        state_ctx = {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.stage,
            "current_agent": state.agent,
            "task": state.task,
            "done": state.done,
            "user_intent": state.user_intent,
            "workflow_metadata": state.workflow_metadata.copy(),
            "history_agents": state.history_agents.copy(),
            "executed_agents_per_stage": state.executed_agents_per_stage.copy(),
        }

        # Include data envelope as dict for predicates
        if isinstance(state.data_raw, DataEnvelope):
            state_ctx["data"] = state.data_raw.payload.model_dump() # dict of RealestateSchema fields
            state_ctx["data_meta"] = { # metadata of the data envelope
                "domain": state.data_raw.domain,
                "type": state.data_raw.type,
                "stage": state.data_raw.stage,
                "producer": state.data_raw.producer,
                "created_at": state.data_raw.created_at.isoformat(),
                "checksum": state.data_raw.checksum,
                "references": state.data_raw.references.copy()
            }
        else:
            # fallback if raw dict or not typed yet
            state_ctx["data"] = state.data_raw
            state_ctx["data_meta"] = {}

        # Include recent tool outputs
        tool_context = []
        if isinstance(state.tool_raw, list):
            for t in state.tool_raw[-5:]:  # last 5 tool executions
                if isinstance(t, ToolEnvelope):
                    tool_context.append({ # metadata of the tool envelope
                        "name": t.tool_name,
                        "success": t.success,
                        "output": t.output,
                        "error": t.error,
                        "stage": t.stage,
                        "agent_role": t.agent_role
                    })
                elif isinstance(t, dict):
                    tool_context.append(t)
        state_ctx["recent_tools"] = tool_context

        logger.info(f"Predicate state context: {state_ctx}")

        return state_ctx


# -----------------------------------------------------------------------------
# ArtifactValidator
# -----------------------------------------------------------------------------
# Deterministic validation layer responsible for enforcing artifact correctness.
#
# ArtifactValidator:
#   - Evaluates the control artifact against structural and policy rules
#   - Derives validation_errors, warnings, and open_tasks
#   - Correlates recent ToolEnvelopes as execution evidence
#   - Updates artifact status and validation metadata
#
# This component represents the "rule of law" of the system:
#   it does not plan, reason, or execute tools,
#   but enforces truth, consistency, and completion guarantees
#   before control is returned to the AgentPlanner.
# -----------------------------------------------------------------------------
class ArtifactValidator:
    def __call__(self, state: StateSchema) -> dict:

        logger.info("*************  Artifact Validator is being called ...")

        artifact = state.control_raw
        artifact.validation_errors.clear()
        artifact.warnings.clear()
        artifact.open_tasks.clear()

        # 1. Structural checks
        if not artifact.current_plan:
            artifact.validation_errors.append("Plan is empty")

        # 2. Task completeness
        open_tasks = [
            t for t in artifact.current_plan if not t.get("completed")
        ]
        artifact.open_tasks.extend(open_tasks)

        # 3. Tool evidence checks
        for tool in state.tool_raw[-5:]:
            if not tool.success:
                artifact.validation_errors.append(
                    f"Tool {tool.tool_name} failed"
                )

        # 4. Status update
        artifact.status = (
            "completed"
            if not artifact.validation_errors and not artifact.open_tasks
            else "running"
        )

        artifact.last_updated = datetime.utcnow()

        return {"control_raw": artifact}


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
class CoreEngine:
    """
    The Orchestration Assembly for the Agnostic OS.
    Wires together the AgentRunner (Execution) and AgentPlanner (Control).
    """
    def __init__(
        self, 
        session_id: str,
        user_intent: str,
        workspace_meta: dict,
        workspace_path: Path
    ):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.session_id = session_id

        self.user_intent = user_intent

        self.domain = workspace_meta.get("domain")

        domain_repo = self.workspace_path.parent.parent / "runtime" / "domain_repo" 

        logger.info(f"Domain Repo: {domain_repo}")

        # --------------------------------------------------
        # 1. Stage Management
        # --------------------------------------------------
        self.stage_manager = StageManager(workspace_path=self.workspace_path)
        self.stage_manager.register_stages()

        # --------------------------------------------------
        # 2. Agent Management
        # --------------------------------------------------
        self.agent_manager = AgentManager(workspace_path=self.workspace_path)
        self.agent_manager.scan_and_register_agents()

        # --------------------------------------------------
        # 3. System Context
        # --------------------------------------------------
        self.context = SystemContext(domain_repo = domain_repo, agent_manager = self.agent_manager)

        # --------------------------------------------------
        # 4. Initial Data Raw Setup 
        # --------------------------------------------------
        # Now based on agent
        #self.initial_data_envelope = self.context.data_manager.get_initial_envelope(domain)

        # --------------------------------------------------
        # 5. LLM Models
        # --------------------------------------------------
        self.agent_llm = self.spin_model()
        self.architect_llm = self.spin_model()
        self.core_llm = self.spin_model()

        # --------------------------------------------------
        # 6. Engine Hemispheres
        # --------------------------------------------------
        self.runner  = AgentRunner(self.context, self.stage_manager, self.agent_manager, self.agent_llm)
        self.planner = AgentPlanner(self.context, self.stage_manager, self.agent_manager, self.architect_llm)
        self.validator = ArtifactValidator()

    # --------------------------------------------------
    # Graph Compilation invoked from orchestrator.py
    # --------------------------------------------------
    def compile(self):
        """
        Wires the nodes into a persistent cyclic state machine.
        """
        workflow = StateGraph(StateSchema)

        # Register the Hemispheres
        workflow.add_node("runner", self.runner)
        workflow.add_node("planner", self.planner)
        workflow.add_node("validator", self.validator)
        
        # Every action is followed by a plan reconciliation
        workflow.add_edge("runner", "validator")
        workflow.add_edge("validator", "planner")
        workflow.add_edge("planner", "runner")
        
        # The Planner's output determines the next step
        workflow.add_conditional_edges(
            "planner",
            self._should_continue
        )

        # Define the entry point to the Logical Flow
        workflow.set_entry_point("planner")

        # Use a 'breakpoint' on the planner node if a human tool was called
        return workflow.compile()
        #return workflow.compile(interrupt_before=["agent"] if self._check_hitl_needed else [])

    # --------------------------------------------------
    # State Instantiation invoked from orchestrator.py
    # --------------------------------------------------
    async def initialize_state(self, user_intent):

        # --------------------------------------------------
        #  Initial Artifact Setup
        # --------------------------------------------------
        # md_text = await self._build_initial_artifact(user_intent)
        # logger.info(f"The initial Artifact: {md_text}")

        #initial_artifact = ArtifactFactory(None).compile(md_text)

        return StateSchema(
            session_id  = self.session_id,
            domain      = self.domain,
            #control_raw = None,         # AgentPlanner chooses the initial_artifact,
            #data_raw    = None,         # AgentPlanner chooses the first agent to get the data_raw
            data_type   = "envelope",
            tool_raw    = [],
            user_intent = user_intent,
            task        = INIT_TASK,    # AgentPlanner chooses the next task
            agent       = "",           # AgentPlanner chooses the next agent
            stage       = "",           # AgentPlanner chooses the next stage
            done        = False,
            history_agents = [], # filled up and generated during orchestration
            executed_agents_per_stage={}, # filled up and generated during orchestration
            workflow_metadata = {
                 "status": "running", 
                 "initial_timestamp": datetime.utcnow().isoformat()
                }
        )

    # --------------------------------------------------
    # Engine Governor: Decide whether to continue mission loop
    # --------------------------------------------------
    def _should_continue(self, state: "StateSchema") -> str:
        """
        Control-plane governor:
        - Checks if tasks remain
        - Checks for HITL requirements
        """
        plan = getattr(state.control_raw, "current_plan", "")
        if "[ ]" not in plan:
            logger.info("[CoreEngine] All tasks completed. Ending mission loop.")
            return "terminal"

        if self._check_hitl_needed(state):
            logger.info("[CoreEngine] HITL required. Pausing at agent node.")
            return "architect"

        return "agent"

    # --------------------------------------------------
    # HITL detection
    # --------------------------------------------------
    def _check_hitl_needed(self, state: "StateSchema") -> bool:
        """
        Determines if last tool execution requires human intervention.
        """
        if not state.tool_raw: 
            return False
        last_tool = list(state.tool_raw.values())[-1][-1]  # last tool envelope
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

    # --------------------------------------------------
    # LLM Model bootstrap
    # --------------------------------------------------

    def spin_model(self):
        llm_dir = self.workspace_path.parent.parent / "llm"
        logger.info(f"[CoreEngine] Bootstrapping LLM model from {llm_dir}")
        return ModelManager(
            chatmodel_provider="ollama:qwen2:0.5b",
            embedding_provider="ollama:nomic-embed-text:latest",
            store_provider="in-memory-ollama",  
            llm_config_dir = llm_dir
        )

# -------------------------------------------------------------------------
# Helper Function
# -------------------------------------------------------------------------
async def hydrate(template: str, variables: Dict[str, Any]) -> str:
    logger.info("Hydrating ...")
    prompt_template = PromptTemplate.from_template(template)
    return prompt_template.invoke(variables).to_string()

def load_file(file_path: Path):

    if not file_path.exists():
        logger.error(f"File path '{file_path}' does not exist")
        raise FileNotFoundError(f"File path '{file_path}' does not exist")

    return file_path.read_text(encoding="utf-8")

async def _call_llm(prompt: str, user_intent: str, model_manager: ModelManager) -> str:

    system_prompt = [
        HumanMessage(content=user_intent), # {"role" : "user", "content" : user_intent },
        SystemMessage(content=prompt)      # {"role" : "system", "content" : prompt }
    ]

    return await model_manager.ainvoke(
        prompt=system_prompt,
        persist=False,
        reflect=False
    )