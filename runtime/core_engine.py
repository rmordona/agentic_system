from __future__ import annotations

import re
import json
from typing import Dict, Any
from datetime import datetime, UTC, timezone
from langgraph.graph import StateGraph, END
from pathlib import Path

import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated, Literal, Optional
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from langgraph.graph.message import add_messages  # optional


from langchain_core.messages import SystemMessage, HumanMessage

from langgraph.errors import GraphInterrupt

from runtime.artifact_factory import Task, ArtifactSchema, ArtifactFactory, HITLState

from llm.model_manager import ModelManager
from runtime.stage_manager import StageSchema, StageManager
from runtime.agent_manager import AgentManager
from runtime.policy_registry import PolicyRegistry, PredicateEngine

from runtime.agent_profiler import AgentProfile

from runtime.domain_manager import DomainType, AgentContext, SystemContext, DataEnvelope, ToolEnvelope, DataAdapter, ToolAdapter

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


class StateSchema(BaseModel):
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    session_id: str
    domain: str
    agentContext: dict[str, AgentContext]
    # ------------------------------------------------------------------
    # Orchestration Fields
    # ------------------------------------------------------------------
    user_intent: str = ""
    task: Task = None
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

    def enforce_allowed_agents(self, agent_name, stage_meta: StageSchema):
        if agent_name not in stage_meta.allowed_agents:
            raise Exception(f"{agent_name} not allowed in stage {stage_meta.name}")

    async def __call__(self, state: StateSchema):
        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentRunner is being called                                  ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"Received state from agent: '{state.agent}', stage: {state.stage}, task: {state.task}")

        user_intent = state.user_intent

        stage      = state.stage        # Received from AgentPlanner
        agent_name = state.agent        # Received from AgentPlanner
        task       = state.task         # Received from AgentPlanner

        logger.info(f"Current Stage: {stage}")
        logger.info(f"Task Received: {task}")
        logger.info(f"Task: {task.id}, description: {task.description}")
        logger.info(f"Tool type: {task.execution}, tool_name: {task.tool_name}")

        stage_meta = self.stage_manager.get(stage)
        self.enforce_allowed_agents(agent_name, stage_meta)

        # Get Agent Context
        agent_ctx = state.agentContext[agent_name]

        # Get Agent Profile
        agent_profile = self.agent_manager.get_agent_profile(agent_name)
        logger.info(f"Agent Profile: {agent_profile}")

        # Get The Artifact for State Control
        artifact = agent_ctx.control_raw

        # Extract tasks to be executed
        artifact.open_tasks = [
            t for t in artifact.current_plan 
            if not t.depends_on
        ]

        logger.info(f"Open Tasks: {len(artifact.open_tasks)}")

        # Process the Data Envelope for Input
        data_env = await self.context.data_manager.process_input(task.tool_name, agent_name, stage, user_intent)
        logger.info(f"Data Envelope with Input Data: {data_env}")
  
        # Execute Tool and retrieve the Tool Envelope
        tool_env = await self.execute_task(task, state, data_env)
        logger.info(f"Tool Envelope: {tool_env}")

        if isinstance(tool_env, ToolEnvelope):
            agent_ctx.tool_raw.append(tool_env)  # Preserve the ToolEnvelope
        # Process the Data Envelope for Output
        data_env = await self.context.data_manager.process_output(task.tool_name, tool_env.output, data_env)
        logger.info(f"Data Envelope with Output Data: {data_env}")
        if isinstance(data_env, DataEnvelope):
            agent_ctx.data_raw = data_env # Preserve the DataEnvelope

        #logger.info(f"agent_ctx.tool_raw: {agent_ctx.tool_raw}")
        #logger.info(f"-------------------------- agentContext: {agent_ctx}")


        state.agentContext[agent_name] = agent_ctx

        '''
        #------
        # 1. Get Agent Prompt (AGENT.md with template to input {task} and {conversation_history}).
        #    The AGENT.md also includes JSON schema for output. This will be the result as payload.
        agent_prompt = self.agent_manager.get_agent_prompt(agent_name)

        # 2. Hydrate Context
        data_adapter = self.context.data_manager.get_adapter(agent_name)
        data_envelope = agent_ctx.data_raw # DataEnvelope.model_validate_json(state.data_raw)
        
        # 3. LLM Inference 
        prompt = self.compose_agent_prompt(state)

        logger.info(f"[AgentRunner] Prompt:  {prompt}")
        response = await self.llm.ainvoke(prompt)

        new_tool_envelopes = []
        updated_payload = data_envelope.payload.copy()
        #------

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

        # Only place holders, will not get sent
        state.agentContext[agent_name].data_raw = new_data_envelope
        state.agentContext[agent_name].tool_raw = new_tool_envelopes
        '''
 
        # Partial Update,  note: graph.astream should have the stream="update"
        return {  "agentContext": state.agentContext }


    async def execute_task(self, task: Task, state: StateSchema, data_env: DataEnvelope) -> ToolEnvelope:
        """
        Execute a single task.
        Mutates task.status and task.result ONLY.
        """
        logger.info(f"Executing task {task.id}: {data_env}")
        agent_ctx = state.agentContext[state.agent]

        try:
            # -------------------------------------------------
            # 1. Build execution prompt / instruction
            # -------------------------------------------------
            instruction = {
                "agent": agent_ctx.agent_name,
                "stage": agent_ctx.stage,
                "task_id": task.id,
                "payload" : data_env.payload,
                "tool_name" : task.tool_name,
                "task_description": task.description,
                "control": agent_ctx.control_raw,
                "data": agent_ctx.data_raw,
            }

            # --------------------------------------------------------------------------------------------
            # 2. Decide execution mode (tool vs LLM)
            # --------------------------------------------------------------------------------------------
            # Always have a second guardrail (_requires_tool) to assist the LLM generated (task.execution)
            result = {}
            if task.execution == "tool":
                try:
                    result =  await self._execute_with_tool(task, instruction)
                except BaseException as e:
                    logger.exception("BaseException escaped from _execute_with_tool", exc_info=e)
                    raise
            elif task.execution == "llm":
                result = await self._execute_with_llm(task, instruction)

            # -------------------------------------------------
            # 3. Persist result
            # -------------------------------------------------
            task.result = result
            if isinstance(result, ToolEnvelope):
                task.result = result.model_dump()

            task.status = "done"

            logger.info(f"Execute Result: {task.result}")

            # Optional: append execution trace
            agent_ctx.result_summary = f"Task {task.id} completed successfully"

            return result

        except Exception as e:
            # -------------------------------------------------
            # 4. Failure handling
            # -------------------------------------------------
            task.status = "blocked"
            task.error = str(e)

            agent_ctx.result_summary = (
                f"Task {task.id} blocked due to error: {str(e)}"
            )
        return None

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    async def _execute_with_tool(self, task: Task, instruction: dict) -> ToolEnvelope:

        logger.info(f"Entering Execution with Tools: {task.tool_name}")


        tool_adapter = await self.context.tool_manager.get_adapter(task.tool_name)
        logger.info(f"Registered tool adapter {tool_adapter}")
        if not tool_adapter:
            raise RuntimeError(f"Tool Adapter for '{tool_name}' not registered")

        return await tool_adapter.execute(task.tool_name, instruction)

    async def _execute_with_llm(self, task: Task, instruction: dict) -> dict:

        # 1. Get Agent Prompt (AGENT.md with template to input {task} and {conversation_history}).
        #    The AGENT.md also includes JSON schema for output. This will be the result as payload.
        agent_prompt = self.agent_manager.get_agent_prompt(agent_name)

        # 2. Get Data Envelope
        data_adapter = self.context.data_manager.get_adapter(agent_name)
        data_envelope = agent_ctx.data_raw # DataEnvelope.model_validate_json(state.data_raw)
        
        # 3. LLM Inference 
        prompt = self.compose_agent_prompt(state)

        logger.info(f"[AgentRunner] Prompt:  {prompt}")
        response = await self.llm.ainvoke(prompt)

        logger.info(f"Get Tool from Tool Manager: {task.tool_name}")
        response = await self.llm.complete(
            system=f"You are {instruction['agent']} executing a task.",
            user=instruction["task_description"],
            context=instruction,
        )

        return {
            "output": response,
        }


        raise RuntimeError("No suitable tool found")


    ###############################################################################
    # Composing Agent Prompt
    ###############################################################################
    def compose_agent_prompt(self, state: StateSchema):

        # Get Agent Context
        agent_ctx = state.agentContext[state.agent]

        # Get Agent Artifact
        artifact = agent_ctx.control_raw

        # Get Agent Profile
        profile = self.agent_manager.get_agent_profile(state.agent)

        # Pull the CURRENT STATE from Data (The Envelope)
        # We look into the payload of the envelope to see what we already know
        data_envelope = agent_ctx.data_raw.model_dump(mode='json')
        current_payload = data_envelope.get("payload") if data_envelope else {}

        logger.info(f"Payload: {current_payload}")

        # 1. Identity & Protocol (Generic)
        system_content = f"""
        ROLE: {profile.role}
        STYLE: {profile.task_style}
        
        PROTOCOL:
        - Compare MISSION to CURRENT_STATE.
        - If CURRENT_STATE is insufficient, use a TOOL to gather more data.
        - Never assume data that is not explicitly in the CURRENT_STATE.
        """

        # 2. State & Mission (The Envelope)
        user_content = f"""
        MISSION: {artifact.mission}
        
        CURRENT_STATE:
        {json.dumps(artifact.spec, indent=2)}
        
        TASKS:
        {[t.description for t in artifact.open_tasks]}

        PAYLOAD: {current_payload}
        """
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

# -----------------------------------------------------------------------------
# AgentValidator
# -----------------------------------------------------------------------------
# Deterministic validation layer responsible for enforcing artifact correctness.
#
# AgentValidator:
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
class AgentValidator:
    def __init__(self):
        self.predicate_engine = PredicateEngine()

    def __call__(self, state: StateSchema) -> dict:
        logger.info("*********************************************************************************************************")
        logger.info("****                              AgentValidator is being called                                   ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"Received state from agent: '{state.agent}', stage: {state.stage}, task: {state.task}")

        agent_ctx = state.agentContext[state.agent]

        artifact = agent_ctx.control_raw

        # -------------------------------
        # 1. Clear previous validation state
        # -------------------------------
        artifact.validation_errors.clear()
        artifact.warnings.clear()
        artifact.open_tasks.clear()
        artifact.hitl = HITLState(required = False)

        # -------------------------------
        # 2. Structural checks
        # -------------------------------
        if not artifact.current_plan:
            artifact.validation_errors.append("Plan is empty")

        # -------------------------------
        # 3. Task completeness
        # -------------------------------
        if artifact.current_plan:
            open_tasks = [t for t in artifact.current_plan if t.status not in ["completed", "done" ]]
            artifact.open_tasks.extend(open_tasks)

        logger.info(f"**** Open Tasks: {artifact.open_tasks}")
 
        # -------------------------------
        # 4. Tool evidence checks
        # -------------------------------
        for tool in agent_ctx.tool_raw[-5:]:
            if not tool.success:
                artifact.validation_errors.append(
                    f"Tool {tool.tool_name} failed"
                )

        # -------------------------------
        # 5. Validate Rules
        # -------------------------------
        logger.info(f"Artifact Validation Errors 1: {artifact.validation_errors}")
        self.validate(state)
        logger.info(f"Artifact Validation Errors 2: {artifact.validation_errors}")

        # -------------------------------
        # 6. Status update
        # -------------------------------

        if artifact.validation_errors:
            artifact.status = "blocked"
            artifact.hitl = HITLState(required = True)
        elif not artifact.open_tasks:
            artifact.status = "completed"
        else:
            artifact.status = "running"

        artifact.last_updated = datetime.now(UTC)

        state.agentContext[state.agent].control_raw = artifact

        return {"agentContext": state.agentContext}


    def validate(self, state: StateSchema):
        # -------------------------------
        # 4.5 Validation rule checks
        # -------------------------------
        agent_ctx = state.agentContext[state.agent]

        # Acquire the input and output data
        context = self._build_context(agent_ctx)
        logger.info(f"Input and Output Context: {context}")

        artifact = agent_ctx.control_raw

        for tool in agent_ctx.tool_raw:
            governance_policy = tool.governance_policy
            rules = governance_policy.get("validation_rules") or {}
            logger.info(f"Governance Rule for tool {tool.tool_name}: {rules}")
            for rule in rules:
                try:
                    gate = self.predicate_engine.parse_predicate(rule)
                    passed = self.predicate_engine.verify(gate, context)
                    if not passed:
                        artifact.validation_errors.append(
                            f"Validation rule failed: {rule}"
                        )
                    logger.info(f"Pass rule: {rule}, verdict: {passed}")
                except Exception as e:
                    artifact.validation_errors.append(
                        f"Invalid validation rule '{rule}': {e}"
                    )


        # -------------------------------
        # 4.6 Stage exit trigger
        # -------------------------------
        artifact.stage_exit_allowed = True  # default

        for tool in agent_ctx.tool_raw:
            governance_policy = tool.governance_policy
            trigger = governance_policy.get("stage_exit_trigger")
            logger.info(f"Governance Exit Trigger for tool {tool.tool_name}: {trigger}")
            if not trigger:
                continue

            try:
                gate = self.predicate_engine.parse_predicate(trigger)
                artifact.stage_exit_allowed = self.predicate_engine.verify(gate, context)
                logger.info(f"Pass stage exit trigger: {trigger}, verdict: {artifact.stage_exit_allowed}")
            except Exception:
                artifact.stage_exit_allowed = False


    def _build_context(self, agent_ctx: AgentContext) -> dict:
        """
        Constructs a context dictionary for predicate evaluation.
        Combines:
        1. Structured data from the DataEnvelope (input/output)
        2. Tool outputs from the last N ToolEnvelope records (authoritative)
        """
        context = {}

        # -------------------------------
        # 1. Data Plane (structured input/output)
        # -------------------------------
        if agent_ctx.data_raw and agent_ctx.data_raw.payload:
            payload_dict = agent_ctx.data_raw.payload.model_dump()
            context.update(payload_dict.get("input", {}))
            context.update(payload_dict.get("output", {}))

        # -------------------------------
        # 2. Tool Plane (authoritative outputs)
        # -------------------------------
        for tool in agent_ctx.tool_raw[-3:]:  # last 3 tools
            if not tool.output:
                continue

            outputs = tool.output if isinstance(tool.output, list) else [tool.output]

            for item in outputs:
                # Case 1: TextContent (legacy MCP)
                if hasattr(item, "text"):
                    try:
                        parsed = json.loads(item.text)
                        if isinstance(parsed, dict):
                            context.update(parsed)
                        else:
                            context[f"raw_output_{tool.tool_name}"] = parsed
                    except Exception:
                        context[f"raw_output_{tool.tool_name}"] = item.text

                # Case 2: dict -> merge directly
                elif isinstance(item, dict):
                    context.update(item)

                # Case 3: str -> parse JSON if possible
                elif isinstance(item, str):
                    try:
                        parsed = json.loads(item)
                        if isinstance(parsed, dict):
                            context.update(parsed)
                        else:
                            context[f"raw_output_{tool.tool_name}"] = parsed
                    except Exception:
                        context[f"raw_output_{tool.tool_name}"] = item

                # Case 4: any other type -> store as-is
                else:
                    context[f"raw_output_{tool.tool_name}"] = item

        return context

    def route_after_validation(self, state:StateSchema):

        logger.info("*******************************************************************************")
        logger.info("*************      Conditional Edge: route_after_validation.      *************")
        logger.info("*******************************************************************************")

        agent_ctx = state.agentContext[state.agent]
        artifact = agent_ctx.control_raw
        tasks = {}
        logger.console("\nTasks to complete: ")
        for open_task in artifact.open_tasks:
            tasks[open_task.id] = open_task.description  
        for current_task in artifact.current_plan:
            marker = "  [ ]"
            if current_task.id not in tasks:
               marker = "  [x]" 
            logger.console(f"{marker} Task {current_task.id}: {current_task.description}")    

        hitl = artifact.hitl
        if hitl.required:
            logger.info("We Require Human-In-The-Loop (HITL) ...")
            return "Route_To_HITL"
        logger.info("Human-In-The-Loop (HITL) not required ... moving to planner")
        return "Route_To_Planner"

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
        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentPlanner is being called                                 ******")
        logger.info("*********************************************************************************************************")

        if state.task.id == INIT_TASK:

            logger.info("This is the first iteration ... So acquiring the first stage and first agent ...")

            return await self.compose_initial_plan(state)
 
        logger.info(f"Beyond the first Iteration: agent: {state.agent}, stage: {state.stage}, task {state.task}")

        stage_meta = self.stage_manager.get(state.stage)

        # ----------------------------------------------------------
        # 1. Determine exit condition to transition to next stage
        # ----------------------------------------------------------
        logger.info(f"Determine exit condition to transition to next stage [validate_route_exit_condition].")
        next_stage = self.validate_route_exit_condition(state)
        if next_stage:
            logger.info(f"It appears we have to transition to next stage:{next_stage}")
            return next_stage

        if not next_stage:
            logger.info(f"No transition to next stage yet ...")
            next_stage = state.stage

        logger.info(f"Current Stage {state.stage},  Next Stage: {next_stage}")

        # ---------------------------------------------------------------------
        # 2. Determine if there are more open tasks to complete for this agent
        # ----------------------------------------------------------------------
        logger.info(f"Determine if there are more open tasks to complete for this agent [validate_route_next_open_task].")
        next_task =  self.validate_route_next_open_task(state)
        if next_task:
            logger.info(f"It appears we have a next task to complete:{next_task}")
            return next_task

        # ------------------------------------------------------------------------
        # 4. If no open task or no next agent, then let's transition to next stage
        # -------------------------------------------------------------------------
        logger.info(f"Switch to the agent context [switch_agent_context]")
        state_ctx = self.switch_agent_context(state)

        logger.info(f"Determine Next Stages: {stage_meta.next_stages}")
        for transition in stage_meta.next_stages:
            logger.info(f"Transition (next stage): {transition}")
            if transition.get("condition") is None:
                logger.info(f"[AgentPlanner] Transitioning to stage '{transition.get("name")}' (unconditional)")
                return self.route_next_stage(state, transition.get("name"))

            compiled_condition = self.predicates.compile(transition.get("condition"))
            condition_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=state.control_raw.model_dump(),
                state_ctx=state_ctx
            )
            logger.info(f"[AgentPlanner] Transition '{transition.get("name")}' condition '{transition.get("condition")}' evaluated to {condition_result}")
            if condition_result:
                return self.route_next_stage(state, transition.get("name"))

        # --------------------------------------------------
        # 5. Summarize last tool executions
        # --------------------------------------------------
        last_tools = [ToolEnvelope.model_validate_json(t) for t in agent_ctx.tool_raw[-5:]]  # last 5 tools
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
    # Engine Governor: Decide whether to continue mission loop
    ###############################################################################
    def _should_continue(self, state: StateSchema) -> str:

        logger.info("*******************************************************************************")
        logger.info("************* Conditional Edge: _should_continue is being called  *************")
        logger.info("*******************************************************************************")

        logger.info(f"Agent: {state.agent}")
  
        agent_ctx = state.agentContext[state.agent]

        logger.info(f"Beyond the first Iteration now with agent: {state.agent}, stage: {state.stage}, task {state.task}")

        artifact = agent_ctx.control_raw
        open_tasks = artifact.open_tasks

        decision = not artifact.validation_errors and bool(artifact.open_tasks)

        logger.info(f"Open tasks: {open_tasks} len: {len(open_tasks)}, decision: {decision}")

        # Only continue if no validation errors and there are open tasks

        '''
        if self._check_hitl_needed(state):
            logger.info("[CoreEngine] HITL required. Pausing at agent node.")
            return "planner"
        '''

        return "runner"


    ###############################################################################
    # Compose The Initial Plan
    ################################################################################
    async def compose_initial_plan(self, state: StateSchema):

        logger.info("Composing initial plan ...")

        # 1. Acquire first stage
        logger.info("Acquiring the first stage")
        first_stage = self.stage_manager.get_entry_stage()

        logger.info(f"First Stage Acquired: {first_stage}")

        # 2. Find the first agent
        logger.info("Acquiring the first agent")
        first_agent = self.find_the_first_agent(state.domain, first_stage)
        logger.info(f"First Agent Acquired: {first_agent}")

        portfolio  = await self.retrieve_agent_portfolio(state, first_agent)

        # data_envelope = portfolio["data_envelope"] 
        artifact = portfolio["artifact"]

        # 3. Update current stage into the portfolio
        artifact.current_stage = first_stage

        #logger.info(f"Acquiring data_envelope: {data_envelope}")
        logger.info(f"Acquiring artifact: {artifact}")

        if artifact.current_plan:
            logger.info(f"Current Plan: {artifact.current_plan}")
            artifact.open_tasks = list(artifact.current_plan)

        if not artifact.open_tasks:
            return None

        next_task = artifact.open_tasks.pop(0)

        logger.info(f"Next Task: {next_task}")

        # When finished, next agent is created
        state.agentContext[first_agent] = AgentContext(
            agent_name=first_agent,
            stage=first_stage,
            control_raw=artifact,
            #data_raw=data_envelope, 
            #tool_raw=[]
        )

        # Given the user’s goal, what is the next concrete responsibility for this agent in this stage?
        return {
            "task" : next_task, 
            "stage" : first_stage,
            "agent" : first_agent,
            "agentContext" : state.agentContext
        }

    ###############################################################################
    # Retrieve Agent's Portfolio
    ################################################################################
    async def retrieve_agent_portfolio(self, state: StateSchema, agent: str):

        # 3. Compose the relevent data source (data envelope) and tools (tool_envelope)
        #logger.info("Acquiring the relevant data source (data envelope)")
        #data_envelope = self.context.data_manager.get_initial_envelope(agent)

        #logger.info("Acquiring the relevant tools set (tool envelope)")
        #tool_envelope = self.context.tool_manager.get_initial_envelope(agent)

        # 4. Get agent profile to build the artifact.
        logger.info("Get the agent profile ...")
        agent_profile = self.agent_manager.get_agent_profile(agent)
        logger.info(f"Agent's Profile: {agent_profile}")

        # 5. Compose the artifact
        logger.info("Now acquiring the first task based on user intent and user profile")
        artifact = await self.build_initial_artifact(state, agent_profile)

        return { "artifact" : artifact }

        '''
        return {
            "artifact" : artifact,
            "data_envelope" : data_envelope,
            "tool_envelope" : tool_envelope
        }
        '''

    ####################################################################################################
    # Find The First Agent
    ####################################################################################################
    def find_the_first_agent(self, domain: str, first_stage: str):

        logger.info("Finding the first agent ...")

        logger.info(f"Allowed Agents: {self.stage_manager.allowed_agents(first_stage)}")

        # Acquire first agent
        first_agent = self.agent_manager.first_agent(
                self.stage_manager.allowed_agents(first_stage)
            )

        if first_agent is None:
            logger.info(f"No agent to handle the first task for stage '{stage}")
            raise Exception(f"No agent to handle the first task for stage '{stage}")

        logger.info(f"Domain: {domain}, First Stage: {first_stage}, First Agent: {first_agent}")  

        return first_agent

    ####################################################################################################
    # Build the Initial Artifact
    ####################################################################################################
    async def build_initial_artifact(self, state: StateSchema, profile: AgentProfile) -> ArtifactSchema:

        logger.info("[AgentPlanner] Extracting the ARCHITECT_TEMPLATE.md from the repo")
        template_repo = self.context.template_repo

        if not template_repo.exists():
            logger.error(f"Workspace path '{templates_dir}' does not exist")
            raise FileNotFoundError(f"Workspace path '{templates_dir}' does not exist")

        # We load both templates
        self.architect_template = ModelManager.read_prompt_template(ModelManager.RUNTIME_TEMPLATE, "ARCHITECT_TEMPLATE.md")
    
        # Get available tools
        tools = self.context.tool_manager.list_available_tools()
        logger.info(f"List of available tools: {tools}")

        # Get corresponding input schemas
        input_schemas = self.context.data_manager.list_available_input_schemas(tools)
        logger.info(f"List of available input schemas: {input_schemas}")

        # 1. Hydrate the INSTRUCTIONS (The System Prompt)
        logger.info("[AgentPlanner] Build Phase: Hydrating the system prompt.")
        system_prompt = ModelManager.hydrate(self.architect_template, {
            "profile_name": profile.name,
            "profile_role" : profile.role,
            "profile_capabilities": profile.capabilities,
            "profile_task_style" : profile.task_style,
            "profile_can_execute_tools" : str(profile.can_execute_tools),
            "profile_forbidden_actions": profile.forbidden_actions,
            "profile_input_schema" : profile.input_schema,
            "profile_output_schema" : profile.output_schema,
            "user_intent" : state.user_intent,
            "available_tools" : str(tools),
        })
        logger.info(f"Agent Planner initial Prompt: {system_prompt}")

        # 2. Get the RAW TASKS from the LLM
        # The LLM only sees the Instructions and the Goal.

        '''
        logger.info("LLM Model Call ...")
        raw_tasks = await _call_llm(prompt=system_prompt, user_intent=state.user_intent, model_manager=self.llm)
        logger.info("LLM Model Call complete ...")

        logger.info(f"raw_tasks: {raw_tasks.content.strip()}") # Response is an AIMessage(content="...")

        task_dict = self.extract_json_from_markdown(raw_tasks.content.strip())

        logger.info(f"task dict: {task_dict}")


        for task in task_dict:
            artifact.current_plan.append(Task(
                id=task.get("id"),
                execution=task.get("execution"),
                tool_name=task.get("tool_name"),
                description=task.get("description"),
                status="pending",
                stage=state.stage
            ))
        '''

        artifact = ArtifactFactory.initialize_from_agent(profile, state.session_id)

        # Just for now temporarily
        artifact.current_plan = []
        artifact.current_plan.append(
            Task(
                id='1',
                execution='tool',
                tool_name='get_market_regime_data',
                description='Calculate the current market value of NVIDIA stock based on its historical price data and volume history.',
                status="pending",
                stage=state.stage
            )
        )
        artifact.current_plan.append(
            Task(
                id='2',
                execution='tool',
                tool_name='search_ticker_news',
                description='Search for the latest news headlines related to NVIDIA stock volatility.',
                status="pending",
                stage=state.stage
            )
        )
        artifact.current_plan.append(
            Task(
                id='3',
                execution='tool',
                tool_name='analyze_earnings_call',
                description='Analyze earnings calls of recent NVIDIA stock calls.',
                status="pending",
                stage=state.stage
            )
        )       

        logger.info(f"Initial Artifact: {artifact}")

        return artifact

    def extract_json_from_markdown(self, md: str) -> list:
        # This pattern looks for ```json (optional) ... content ... ```
        # It uses a non-greedy match (.*?) to find the first block
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
        
        if match:
            json_str = match.group(1).strip()
        else:
            # Fallback: maybe there are no fences at all
            json_str = md.strip()
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extracted string: {json_str}")
            raise e

            return json.loads(json_str)



    ###############################################################################
    # Routing To Next Open Task
    ################################################################################
    def validate_route_exit_condition(self, state: StateSchema) -> dict:

        agent_ctx = state.agentContext[state.agent]

        logger.info(f"Current Stage: {state.stage}")
        stage_meta = self.stage_manager.get(state.stage)

        logger.info(f"[AgentPlanner] Evaluating Exit Condition for stage '{state.stage}'")
        if stage_meta.exit_condition:
            logger.info(f"[AgentPlanner] Evaluate exit condition '{stage_meta.exit_condition}")

            compiled_condition = self.predicates.compile(stage_meta.exit_condition)
            logger.info(f"[AgentPlanner] Exit condition '{stage_meta.exit_condition}' and compiled: '{compiled_condition}'")

            logger.info(f"Switch to the agent context")
            state_ctx = self.switch_agent_context(state)

            exit_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=agent_ctx.control_raw.model_dump(),
                state_ctx=state_ctx,
            )

            logger.info(f"[AgentPlanner] Exit Condition result: {exit_result}")
            if not exit_result:
                logger.info(f"[AgentPlanner] Stage '{state.stage}' incomplete, tackle next open task or next agent")
                return {"control_raw" : agent_ctx.control_raw }
        return None



    ###############################################################################
    # Routing To Next Open Task
    ################################################################################
    def validate_route_next_open_task(self, state: StateSchema) -> dict:

        agent_ctx = state.agentContext[state.agent]
        artifact = agent_ctx.control_raw

        logger.info(f"Artifact: {artifact}")

        # 1. If artifact is blocked or completed → stop
        if artifact.status in ("blocked", "completed", "aborted"):
            return {"next": "end", "reason" : artifact.status }

        # 2. If there are open tasks → route to agent runner
        if artifact.open_tasks:
            next_task = artifact.open_tasks[0]

            return {
                "next": "runner",
                "task": next_task,
                "stage": artifact.current_stage
            }

        # 3. No open tasks → re-plan or validate
        return {"next": "validator"}


    ###############################################################################
    # Routing To Next Agent
    ################################################################################
    def validate_route_next_agent(self, state: StateSchema) -> dict | None:
        """
        Decide which agent should run next within the current stage.
        Runs agents sequentially per stage.
        """
        stage = state.current_stage
        if not stage:
            return None

        # Agents allowed to run in this stage
        allowed_agents = self.stage_manager.allowed_agents(stage)

        # Ensure execution tracking exists
        if stage not in state.executed_agents_per_stage:
            state.executed_agents_per_stage[stage] = []

        executed = state.executed_agents_per_stage[stage]

        # Determine remaining agents for this stage
        remaining = [agent for agent in allowed_agents if agent not in executed]

        # No agents left → stage is complete
        if not remaining:
            return None

        next_agent = remaining[0]

        # Allowed: factual bookkeeping
        # Changes to this state is not carried over. It needs to be returned partially
        # but we use this for convenience
        state.executed_agents_per_stage[stage].append(agent_name)
        state.history_agents.append(agent_name)

        # Retrieve Agent's Portfolio / Suitecase
        portfolio = self.retrieve_agent_portfolio(state, first_agent)

        if state.agentContext[next_agent]:
           state.agentContext[next_agent].control_raw =  portfolio.artifact
           state.agentContext[next_agent].data_raw = portfolio.data_envelope
        else:
            # When finished, next agent is created
            runner_context = AgentContext(
                agent_name=next_agent,
                stage=stage,
                control_raw=artifact,
                data_raw=data_envelope, 
                tool_raw={ tool_result }
            )
            state.agentContext[next_agent] = runner_context

        return {
            "agent": next_agent,
            "agentContext" : state.agentContex,
            "executed_agents_per_stage" : state.executed_agents_per_stage,
            "history_agents" : state.history_agents,
        }


    ###############################################################################################
    # Transition Phase: we advance to next stage following correct exit conditions
    ################################################################################################
    def route_next_stage(self, state: StateSchema, next_stage: str) -> dict:
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



    #########################################################################################################
    # Transfer to a new agent context.
    #    agent_context.data_raw  # DataEnvelope[RealestateSchema]
    #    ctx["data"]             # dict of RealestateSchema fields
    #    ctx["data_meta"]        # metadata of the data envelope
    #    ctx["recent_tools"]     # metadata of the tool envelope - last 5 tool executions as dicts
    #    ctx["current_stage"] = state.stage
    ##########################################################################################################
    def switch_agent_context(self, state: StateSchema) -> dict:
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
        agent_context = state.agentContext[state.agent]
        agent_data = agent_context.data_raw

        # Include data envelope as dict for predicates
        if isinstance(agent_data, DataEnvelope):
            state_ctx["data"] = agent_data.payload.model_dump() # dict of RealestateSchema fields
            state_ctx["data_meta"] = { # metadata of the data envelope
                "tool": agent_data.tool,
                "type": agent_data.type,
                "stage": agent_data.stage,
                "producer": agent_data.producer,
                "created_at": str(agent_data.created_at),
                "checksum": agent_data.checksum,
                "references": agent_data.references.copy()
            }
        else:
            # fallback if raw dict or not typed yet
            state_ctx["data"] = agent_data
            state_ctx["data_meta"] = {}

        # Include recent tool outputs
        agent_tool = agent_context.tool_raw

        tool_context = []
        if isinstance(agent_tool, list):
            for t in agent_tool[-5:]:  # last 5 tool executions
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


    ###############################################################################
    # Replan as required, but his may need confirmation from HITL
    ################################################################################
    def replan(self, artifact: ArtifactSchema, observation: str):
        # The Planner prompt focuses on the 'Big Picture'
        prompt = f"""
        Current Mission: {artifact.mission}
        Current Plan: {artifact.current_plan}
        New Observation: {observation}
        
        Task: Re-evaluate the open tasks. Add, remove, or re-order tasks 
        to ensure the mission succeeds. Output the updated task list as JSON.
        """
        
        # LLM provides the NEW list of tasks
        new_tasks_payload = self.llm.ainvoke(prompt, response_format=TaskListSchema)
        
        # MUTATION: The Planner updates the Data Envelope
        artifact.open_tasks = new_tasks_payload.tasks
        artifact.plan_history.append(f"Replanned at {datetime.now(UTC)}: {observation}")



####################################################################################################
# AgentHITL
#
# Human-In-The-Loop (HITL) Control Node for Agentic Pipelines
#
# PURPOSE
# -------
# AgentHITL is a dedicated LangGraph node responsible for enforcing human approval
# checkpoints *after* all automated validation has passed.
#
# This node must remain logically separate from validation to preserve:
#   - Determinism
#   - Replayability
#   - Auditability
#   - Testability
#
# CONTRACT
# --------
# Preconditions:
#   - ArtifactValidator has already executed
#   - artifact.status == "ready_for_exit"
#
# Responsibilities:
#   - Decide whether human approval is required
#   - Interrupt execution when HITL is required
#   - Resume execution after approval / rejection
#
# Outcomes:
#   - approved   → pipeline continues
#   - rejected   → artifact blocked
#   - timeout    → configurable fail / approve behavior
#
####################################################################################################


class AgentHITL:
    """
    Production-grade HITL enforcement node.
    """
    def __init__( self,context: SystemContext, auto_approve: bool = False,timeout_seconds: int | None = None,fail_on_timeout: bool = True):
        self.context = context 
        self.auto_approve = auto_approve
        self.timeout_seconds = timeout_seconds
        self.fail_on_timeout = fail_on_timeout

    # ------------------------------------------------------------------
    # LangGraph Node Entry Point
    # ------------------------------------------------------------------
    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentHITL is being called                                    ******")
        logger.info("*********************************************************************************************************")

        user_intent = state.user_intent

        stage      = state.stage        # Received from AgentPlanner
        agent_name = state.agent        # Received from AgentPlanner
        task       = state.task         # Received from AgentPlanner

        logger.info(f"Current Stage: {stage}")
        logger.info(f"User Intent: {user_intent}")
        logger.info(f"Task Received: {task}")
        logger.info(f"Task: {task.id}, description: {task.description}")
        logger.info(f"Tool type: {task.execution}, tool_name: {task.tool_name}")

        agent_ctx = state.agentContext[agent_name]
        artifact = agent_ctx.control_raw

        logger.info(f"Passed 1")
        await self._request_hitl(state)
        # --------------------------------------------------------------
        # Guard: HITL only applies after successful validation
        # --------------------------------------------------------------
        if artifact.status != "ready_for_exit":
            return { "agentContext": state.agentContext }

        logger.info(f"Passed 2")

        # --------------------------------------------------------------
        # Guard: HITL explicitly not required
        # --------------------------------------------------------------
        hitl = artifact.hitl
        if not hitl or not hitl.required:
            return {"agentContext": state.agentContext}

        logger.info(f"Passed 3")

        # --------------------------------------------------------------
        # Auto-approve mode (tests / CI / replay)
        # --------------------------------------------------------------
        if self.auto_approve:
            self._approve(artifact, reason="auto_approve")
            return {"agentContext": state.agentContext}

        logger.info(f"Passed 4")

        # --------------------------------------------------------------
        # Resume path: human has already responded
        # --------------------------------------------------------------
        if hitl.approved is not None:
            if hitl.approved:
                artifact.status = "approved"
            else:
                artifact.status = "blocked"
                artifact.validation_errors.append(
                    hitl.comments or "HITL rejected"
                )

            artifact.last_updated = self._now()
            return {"agentContext": state.agentContext}

        logger.info(f"Passed 5")

        # --------------------------------------------------------------
        # Timeout handling
        # --------------------------------------------------------------
        if self._is_timed_out(hitl):
            if self.fail_on_timeout:
                self._reject(artifact, reason="HITL timeout")
            else:
                self._approve(artifact, reason="HITL timeout auto-approve")

            return {"agentContext": state.agentContext}

        logger.info(f"Passed 6")

        # --------------------------------------------------------------
        # Interrupt graph execution for human input
        # --------------------------------------------------------------
        self._request_hitl(artifact)

        raise GraphInterrupt(
            reason="HITL approval required",
            payload=self._build_payload(state, artifact),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request_hitl(self, state):

        user_intent = state.user_intent
        agent_name  = state.agent
        task        = state.task

        agent_ctx = state.agentContext[agent_name]
        artifact = agent_ctx.control_raw

        hitl = artifact.hitl

        artifact.validation_errors

        data_env = agent_ctx.data_raw
        payload = data_env.payload.model_dump()
        normalized_payload = format_dict_readable(payload)
        logger.info(f"Payload: {normalized_payload}")

        # Get the last tool used
        tool = agent_ctx.tool_raw[-1:][0]
        logger.info(f"Tool: {tool}")
        if isinstance(tool, ToolEnvelope):
            governance_policy = tool.governance_policy
            validation_rules = format_dict_readable(governance_policy.get("validation_rules"))
            hitl_policy = format_dict_readable(governance_policy.get("hitl_policy"))
            logger.info(f"Validation Rules: {validation_rules}")
            logger.info(f"HITL Policy: {hitl_policy}")

        #failed = format_list_readable(artifact.validation_errors)
        
        llm = ModelManager.spin_model()

        prompt = ModelManager.read_prompt_template(ModelManager.RUNTIME_TEMPLATE, 'HITL_TEMPLATE.md')
        prompt = ModelManager.hydrate(prompt, {
            "USER_INTENT" : user_intent,
            "TOOL" : task.tool_name,
            "REQUIREMENT" : validation_rules,
            "CONSTRAINT" : hitl_policy,
            "INVALID_VALUE" : artifact.validation_errors
         })

        logger.info(f"Prompt: {prompt}")
        response = await llm.ainvoke(prompt)

        # ArtifactFactory.show_tasks(artifact.open_tasks)
        logger.console(f"\n**Assistant**: {response.content}")

        artifact.status = "awaiting_human"
        user_response = input("\n>>> Provide guidance: ")

    def _approve(self, artifact, reason: str):
        hitl = artifact.hitl
        hitl.approved = True
        hitl.comments = reason
        hitl.resolved_at = self._now()
        artifact.status = "approved"
        artifact.last_updated = hitl.resolved_at

    def _reject(self, artifact, reason: str):
        hitl = artifact.hitl
        hitl.approved = False
        hitl.comments = reason
        hitl.resolved_at = self._now()
        artifact.status = "blocked"
        artifact.validation_errors.append(reason)
        artifact.last_updated = hitl.resolved_at

    def _is_timed_out(self, hitl) -> bool:
        if not self.timeout_seconds:
            return False
        if not hitl.requested_at:
            return False

        elapsed = (self._now() - hitl.requested_at).total_seconds()
        return elapsed > self.timeout_seconds

    def _build_payload(self, state, artifact) -> Dict[str, Any]:
        """
        Payload sent to the human interface layer (UI, Slack, CLI, etc).
        """
        return {
            "agent": state.agent,
            "stage": artifact.stage,
            "reason": artifact.hitl.reason,
            "artifact": artifact,
            "context_snapshot": state,
        }




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

        self.template_repo = self.workspace_path.parent.parent / "runtime" / "domain_repo" / "templates" 

        logger.info(f"Template Repo: {self.template_repo}")

    async def initialize(self):

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
        self.context = await SystemContext.create(template_repo = self.template_repo, workspace_path = self.workspace_path, agent_manager = self.agent_manager)

        # --------------------------------------------------
        # 4. Initial Data Raw Setup 
        # --------------------------------------------------
        # Now based on agent
        #self.initial_data_envelope = self.context.data_manager.get_initial_envelope(domain)

        # --------------------------------------------------
        # 5. LLM Models
        # --------------------------------------------------
        self.agent_llm = ModelManager.spin_model()
        self.architect_llm = ModelManager.spin_model()
        self.core_llm = ModelManager.spin_model()

        # --------------------------------------------------
        # 6. Engine Hemispheres
        # --------------------------------------------------
        #    Planner → creates intent
        #    Runner → executes tools
        #    Validator → enforces truth
        #    PredicateEngine → is the law
        #    _should_continue → just checks the verdict

        self.validator = AgentValidator()
        self.runner    = AgentRunner(self.context, self.stage_manager, self.agent_manager, self.agent_llm)
        self.planner   = AgentPlanner(self.context, self.stage_manager, self.agent_manager, self.architect_llm)
        self.hitl      = AgentHITL(self.context, True, 10, True )

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
        workflow.add_node("runner", self.runner)
        workflow.add_node("planner", self.planner)
        workflow.add_node("validator", self.validator)
        workflow.add_node("hitl", self.hitl)
        
        # Every action is followed by a plan reconciliation
        workflow.add_edge("runner", "validator")
        #workflow.add_edge("validator", "planner") # This is replaced by a conditional edge to support HITL
        workflow.add_edge("planner", "runner")
        
        # The Planner's output determines the next step
        workflow.add_conditional_edges("planner", self.planner._should_continue )

        # Define the entry point to the Logical Flow
        workflow.set_entry_point("planner")

        workflow.add_conditional_edges(
            "validator",
            self.validator.route_after_validation,
            {
                "Route_To_HITL": "hitl",
                "Route_To_Planner": "planner"
            }
        )


        # Use a 'breakpoint' on the planner node if a human tool was called
        return workflow.compile()
        #return workflow.compile(interrupt_before=["agent"] if self._check_hitl_needed else [])

    # --------------------------------------------------
    # State Instantiation invoked from orchestrator.py
    # --------------------------------------------------
    async def initialize_state(self, user_intent):

        init_task = Task(id=INIT_TASK, description="Initial Task", stage="")

        # Number one rule from AI: "The world looks different depending on who currently holds the token."
        # control_raw, data_raw, and tool_raw should be re-contextualized every time we switch agency
        return StateSchema(
            session_id  = self.session_id,
            domain      = self.domain,
            agentContext = {},
            data_type   = "envelope",
            user_intent = user_intent,
            task        = init_task,    # AgentPlanner chooses the next task
            agent       = "",           # AgentPlanner chooses the next agent
            stage       = "",           # AgentPlanner chooses the next stage
            done        = False,
            history_agents = [], # filled up and generated during orchestration
            executed_agents_per_stage={}, # filled up and generated during orchestration
            workflow_metadata = {
                 "status": "running", 
                 "initial_timestamp": datetime.now(UTC).isoformat()
                }
        )



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


# -------------------------------------------------------------------------
# Helper Function
# -------------------------------------------------------------------------

def _now():
    return datetime.now(timezone.utc)


def format_list_readable(items: list[dict]) -> str:
    lines = []

    for item in items:
        values = list(item.values())

        if not values:
            continue

        # First value becomes main bullet
        lines.append(f"- {values[0]}")

        # Remaining values become indented sub-points
        for value in values[1:]:
            lines.append(f"  • {value}")

        lines.append("")

    return "\n".join(lines).strip()

def format_dict_readable(data, indent: int = 0) -> str:
    lines = []
    space = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            pretty_key = key.replace("_", " ").title()

            if isinstance(value, dict):
                lines.append(f"{space}- {pretty_key}:")
                lines.append(
                    format_dict_readable(value, indent + 1)
                )

            elif isinstance(value, list):
                lines.append(f"{space}- {pretty_key}:")
                for item in value:
                    lines.append(
                        format_dict_readable(item, indent + 1)
                    )

            else:
                lines.append(f"{space}- {pretty_key}: {value}")

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(
                    format_dict_readable(item, indent)
                )
            else:
                lines.append(f"{space}- {item}")

    else:
        lines.append(f"{space}- {data}")

    return "\n".join(lines)




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


