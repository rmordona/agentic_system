from typing import Dict, Any, Optional
from dataclasses import asdict
from runtime.logger import AgentLogger

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import AgentContext

from runtime.domain_manager import SystemContext
from runtime.stage_manager import StageSchema, StageManager

logger = AgentLogger.get_logger(component="system")


################################################################################
# AgentGovernance
################################################################################
# Macro-level orchestration node for a LangGraph-based multi-agent system.
#
# Responsibilities:
# - Evaluate stage exit conditions to determine workflow transitions.
# - Select the next allowed agent for the current stage.
# - Route execution to AgentRunner, AgentPlanner, or HITL as needed.
# - Maintain stage-level execution context and history.
# - Build a predicate context for evaluating conditional transitions.
#
# Inputs:
# - state: StateSchema instance containing current stage, active agent, and workflow metadata.
#
# Outputs:
# - Dict indicating next stage, next agent, and/or next task to execute.
################################################################################
class AgentGovernance:
    def __init__(self, context: SystemContext):
        self.context = context

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentGovernance is being called                                ******")
        logger.info("*********************************************************************************************************")

        self.stage_manager = self.context.stage_manager
        self.agent_manager = self.context.agent_manager

        logger.info(f"State Type: {type(state)}")
        logger.info(f"State: {state}")
        logger.info(f"Workspace: {state.workspace_name}")

        logger.info(f"Agent: {state.active_agent}, stage: {state.stage}, task {state.task}")

        logger.info(f"Current Stage: {state.stage}, Active Agent: {state.active_agent}")

        # Evaluate task
        if state.task is None:
            logger.info(f"No Task. Directly passing to Planner.")
            return {} # No change in state, let Planner handle tasks

        # Check for next open task
        next_task = self._next_open_task(state)
        if next_task:
            logger.info(f"If Next Task, Passing to route_to_next_task.")
            return {} # No change in state, let Planner handle tasks

        # Determine next agent in stage
        next_agent = self._next_agent(state)
        if next_agent:
            logger.info(f"If Next Agent, Passing to route_to_next_task.")
            return next_agent

        # Evaluate stage exit conditions
        next_stage = self._evaluate_stage_exit(state)
        if next_stage:
            logger.info(f"If Next Stage, Passing to route_to_next_stage.")
            return self._route_to_next_stage(state, next_stage)

        # Default: remain in current stage
        return {"stage": state.stage, "active_agent": state.active_agent}

    def _evaluate_stage_exit(self, state: StateSchema) -> Optional[str]:
        stage_meta = self.stage_manager.get(state.stage)
        if not stage_meta.exit_condition:
            return None
        agent_ctx = state.get_active_agent()

        compiled = self.stage_manager.compile_predicate(stage_meta.exit_condition)
        ctx = self._build_state_context(state, agent_ctx)
        artifact = asdict(agent_ctx.control_raw)
        result = self.stage_manager.evaluate_predicate(compiled, ctx, artifact)
        logger.info(f"Stage exit condition {stage_meta.exit_condition} evaluated to {result}")
        return stage_meta.next_stages[0]["name"] if result else None

    def _next_open_task(self, state: StateSchema) -> Optional[Dict[str, Any]]:
        artifact = state.get_active_agent().control_raw
        return artifact.open_tasks

    def _next_agent(self, state: StateSchema) -> Optional[Dict[str, Any]]:
        stage = state.stage
        executed = state.executed_agents_per_stage.get(stage, [])
        allowed_agents = self.stage_manager.allowed_agents(stage)
        remaining_agents = [a for a in allowed_agents if a not in executed]
        if not remaining_agents:
            return None
        next_agent = remaining_agents[0]
        state.executed_agents_per_stage.setdefault(stage, []).append(next_agent)
        state.history_agents.append(next_agent)
        return {"active_agent": next_agent, "stage": stage}

    def _route_to_next_stage(self, state: StateSchema, next_stage: str) -> Dict[str, Any]:
        allowed_agents = self.stage_manager.allowed_agents(next_stage)
        if not allowed_agents:
            raise RuntimeError(f"No allowed agents for stage {next_stage}")
        first_agent = self.agent_manager.first_agent(allowed_agents)
        return {"stage": next_stage, "active_agent": first_agent}

    def _build_state_context(self, state: StateSchema, agent_ctx: AgentContext) -> dict:
        ctx = {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.stage,
            "current_agent": state.active_agent,
            "task": state.task,
            "done": state.done,
            "user_intent": state.normalized_intent,
            "workflow_metadata": state.workflow_metadata.copy(),
            "history_agents": state.history_agents.copy(),
            "executed_agents_per_stage": state.executed_agents_per_stage.copy(),
        }
        ctx["recent_tools"] = [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in agent_ctx.tool_raw[-5:]
        ]
        if hasattr(agent_ctx.data_raw, "payload"):
            ctx["data"] = agent_ctx.data_raw.payload
        else:
            ctx["data"] = agent_ctx.data_raw
        return ctx

