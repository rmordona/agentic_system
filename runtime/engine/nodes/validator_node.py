from __future__ import annotations
from datetime import datetime, UTC

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import AgentContext
from runtime.engine.domain.task import HITLState

from runtime.policy_registry import PredicateEngine

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

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

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                              AgentValidator is being called                                   ******")
        logger.info("*********************************************************************************************************")
        logger.info(f"Received state from agent: '{state.active_agent}', stage: {state.stage}, task: {state.task}")

        # Get Agent Context
        agent_ctx = state.get_active_agent()  

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
        current_plan = artifact.current_plan
        if current_plan:
            open_tasks = [t for t in current_plan if t.get("status") not in ["completed", "done" ]]
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

------
            if intent_type == "unknown":
                return {
                    "human_response": None,
                    "hitl_required": True,
                    "hitl_type": "intent_clarification",
                    "hitl_prompt": "I couldn't understand your request. Could you please rephrase what you'd like to do?",
                    "hitl_resume_node": "refiner"
                }
------

        elif not artifact.open_tasks:
            artifact.status = "completed"
        else:
            artifact.status = "running"

        artifact.last_updated = datetime.now(UTC)

        agent_ctx.control_raw = artifact

        logger.info(f"Data Raw: {agent_ctx.data_raw}")

        state.update_active_agent(agent_ctx)

        return {"agents": state.agents}


    def validate(self, state: StateSchema):
        # -------------------------------
        # 4.5 Validation rule checks
        # -------------------------------

        agent_ctx = state.get_active_agent()  

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

        logger.info(f"Agent Context: {agent_ctx}")
        # -------------------------------
        # 1. Data Plane (structured input/output)
        # -------------------------------
        if agent_ctx.data_raw:
            data_raw = agent_ctx.data_raw
            if data_raw.payload:
                payload_dict = data_raw.payload
                context.update(payload_dict.get("input"))
                context.update(payload_dict.get("output"))

        # -------------------------------
        # 2. Tool Plane (authoritative outputs)
        # -------------------------------
        for tool in agent_ctx.tool_raw[-3:]:  # last 3 tools

            logger.info(f"tool: {tool}")

            if not tool.output:
                continue

            tool_output = tool.output

            outputs = tool_output if isinstance(tool_output, list) else [tool_output]

            logger.info(f"tool output: {outputs}")

            for item in outputs:
                # Case 1: TextContent (legacy MCP)
                logger.info(f"tool output item: {item}")
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

        # Get Agent Context
        agent_ctx = state.get_active_agent()  

        artifact = agent_ctx.control_raw
        tasks = {}
        logger.console("\nTasks to complete: ")
        for open_task in artifact.open_tasks:
            tasks[open_task.get("id")] = open_task.get("description")
        for current_task in artifact.current_plan:
            marker = "  [ ]"
            if current_task.get("id") not in tasks:
               marker = "  [x]" 
            logger.console(f"{marker} Task {current_task.get("id")}: {current_task.get("description")}")    

        logger.info(f"Artifact: {artifact}")

        hitl = artifact.hitl
        if hitl.get("required"):
            logger.info("We Require Human-In-The-Loop (HITL) ...")
            return "Route_To_HITL"
        logger.info("Human-In-The-Loop (HITL) not required ... moving to planner")
        return "Route_To_Refiner"