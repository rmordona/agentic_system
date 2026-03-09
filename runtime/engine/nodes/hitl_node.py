from typing import Dict, Any, Union

from langgraph.types import interrupt, Command

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.envelopes import ToolEnvelope

from runtime.domain_manager import SystemContext
from llm.model_manager import ModelManager

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

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
    Handles human-in-the-loop approval for tasks.
    """
    def __init__(
        self,
        context: SystemContext,
        auto_approve: bool = False,
        timeout_seconds: int | None = None,
        fail_on_timeout: bool = True,
    ):
        self.context = context
        self.auto_approve = auto_approve
        self.timeout_seconds = timeout_seconds
        self.fail_on_timeout = fail_on_timeout

        self.llm = ModelManager.spin_model()

    # ------------------------------------------------------------------
    # LangGraph Node Entry Point
    # ------------------------------------------------------------------
    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        # Ensure we are working with a Pydantic object, even after resume
        # This is a classic "de-serialization" hurdle in LangGraph. When you use a custom Pydantic class like StateSchema 
        # as your state, LangGraph’s checkpointer (Postgres or Memory) has to save that data as JSON. When the graph resumes, 
        # it tries to rebuild your state from that JSON.

        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentHITL is being called                                    ******")
        logger.info("*********************************************************************************************************")
        logger.info(f"State Type: {type(state)}")
        logger.info(f"State: {state}")

        # ------------------------------------
        # RESUME PATH
        # ------------------------------------
        if state.human_response:

            response = state.human_response
            resume_node = state.hitl_resume_node

            logger.info(f"Resuming to {resume_node} with human input: {response}")

            return Command(
                goto=resume_node,
                update={
                    "human_response": response,
                    "hitl_required": False
                }
            )

        # ------------------------------------
        # INTERRUPT PATH
        # ------------------------------------
        prompt = state.hitl_prompt or "User input required."

        logger.info(f"Now interrupting for HITL ... Awaiting user response ...")
        logger.info(f"Note: websocket receiver is (frontend/src/hooks/useChat.ts)")
        resume =  interrupt({
            "type": state.hitl_type,
            "prompt": prompt
        })

        return Command(
            goto=state.hitl_resume_node,
            update={
                "human_response": resume.get("human_response"),
                "hitl_required": False
            }
        )

        '''
        logger.info(f"Now interrupting for HITL ... Awaiting user response ...")
        resume = interrupt({
            "type": "hitl_required",
            "prompt": response.content,
            "agent": state.active_agent,
            "task_id": task.id,
        })
        logger.error(f"THIS SHOULD NEVER PRINT: {resume}")
        return Command(
                goto="runner",
                update={
                    "human_response": resume.get("human_response"),
                    "retry_count": state.retry_count + 1
                }
            )
        '''

        # --------------------------------------------------
        # RESUME AFTER INTERRUPT
        # --------------------------------------------------
        logger.info(f"State human_response at entry: {state.human_response}")
        '''
        # 1. Check if we just came back from an interrupt
        if state.human_response:
            logger.info(f"Resumed! User said: {state.human_response}")
            user_feedback = state.human_response
            
            # CLEAR the response so the next HITL node starts fresh
            return {
                "human_response": None, 
                "hitl_completed": True,
                "approved": True if "yes" in user_feedback.lower() else False
            }
        '''

        # --------------------------------------------------
        # NORMAL EXECUTION PATH
        # --------------------------------------------------
        user_intent = state.user_intent
        stage      = state.stage
        agent_name = state.active_agent
        task       = state.get_task() 

        logger.info(f"Current Stage: {stage}")
        logger.info(f"User Intent: {user_intent}")
        logger.info(f"Task Received: {task}")
        logger.info(f"Task: {task.id}, description: {task.description}")
        logger.info(f"Tool type: {task.execution}, tool_name: {task.tool_name}")


        agent_ctx = state.get_active_agent()
        artifact = agent_ctx.control_raw

        # --------------------------------------------------
        # Generate HITL prompt for the user
        # --------------------------------------------------
        response = await self._request_llm_for_hitl(state)
        logger.info(f"Model response received ...")

        # --------------------------------------------------
        # INTERRUPT GRAPH & WAIT FOR HUMAN RESPONSE
        # --------------------------------------------------
        # Important: Do NOT assign interrupt() to a variable.
        # LangGraph will pause execution here and save the checkpoint.

        logger.info(f"Now interrupting for HITL ... Awaiting user response ...")
        resume = interrupt({
            "type": "hitl_required",
            "prompt": response.content,
            "agent": state.active_agent,
            "task_id": task.id,
        })
        logger.error(f"THIS SHOULD NEVER PRINT: {resume}")
        return Command(
                goto="runner",
                update={
                    "human_response": resume.get("human_response"),
                    "retry_count": state.retry_count + 1
                }
            )


        '''
        # The interrupt will stop the node and resumes by re-entering the done 
        # upon human response.


        ######### ------------------------------- below may not be required

        # --------------------------------------------------------------
        # Guard: HITL only applies after successful validation
        # --------------------------------------------------------------
        if artifact.status != "ready_for_exit":
            return { "agentContext": state.agentContext }

        # --------------------------------------------------------------
        # Guard: HITL explicitly not required
        # --------------------------------------------------------------
        hitl = artifact.hitl
        if not hitl or not hitl.required:
            return {"agentContext": state.agentContext}

        # --------------------------------------------------------------
        # Auto-approve mode (tests / CI / replay)
        # --------------------------------------------------------------
        if self.auto_approve:
            self._approve(artifact, reason="auto_approve")
            return {"agentContext": state.agentContext}

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

        # --------------------------------------------------------------
        # Timeout handling
        # --------------------------------------------------------------
        if self._is_timed_out(hitl):
            if self.fail_on_timeout:
                self._reject(artifact, reason="HITL timeout")
            else:
                self._approve(artifact, reason="HITL timeout auto-approve")

            return {"agentContext": state.agentContext}
        '''

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _request_llm_for_hitl(self, state: StateSchema):

        user_intent = state.user_intent
        agent_name  = state.active_agent
        task        = state.get_task()

        agent_ctx = state.get_active_agent()
        artifact = agent_ctx.control_raw

        hitl = artifact.hitl

        artifact.validation_errors

        data_env = agent_ctx.data_raw
        payload = data_env.payload
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
        
        prompt = ModelManager.read_prompt_template(ModelManager.RUNTIME_TEMPLATE, 'HITL_TEMPLATE.md')
        prompt = ModelManager.hydrate(prompt, {
            "USER_INTENT" : user_intent,
            "TOOL" : task.tool_name,
            "REQUIREMENT" : validation_rules,
            "CONSTRAINT" : hitl_policy,
            "INVALID_VALUE" : artifact.validation_errors
         })

        logger.info(f"Prompt: {prompt}")
        response = await self.llm.ainvoke(prompt)

        return response

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
            "agent": state.active_agent,
            "stage": artifact.stage,
            "reason": artifact.hitl.reason,
            "artifact": artifact,
            "context_snapshot": state,
        }


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


