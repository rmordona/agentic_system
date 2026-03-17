from __future__ import annotations
from typing import Any, Dict, Optional
from langgraph.graph import END
from runtime.logger import AgentLogger
from runtime.engine.state.state_schema import StateSchema
from runtime.engine.state.state_mapper import to_agent_context, to_storage
from runtime.engine.domain.task import HITLState
from runtime.domain_manager import AgentManager, SystemContext
from runtime.engine.stage.stage_manager import StageManager
from runtime.engine.governance.governance_manager import GovernanceManager, GovernanceViolation

logger = AgentLogger.get_logger(component="system")


class AgentGovernance:
    """
    LangGraph node: AgentGovernance
    Responsibilities:
    - Evaluate stage exit conditions
    - Validate agent output via GovernanceManager
    - Determine next stage and agent
    - Trigger HITL if required
    - Route execution (Planner, Runner)
    """

    def __init__(self, context: SystemContext):
        self.context: SystemContext = context

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info(f"=== AgentGovernance called: stage={state.stage_name}, agent={state.active_agent} ===")

        artifact = self._get_current_artifact(state)
        state_ctx = self._build_state_ctx(state)

        # 1️⃣ Validate agent action
        agent_schema = self.context.agent_manager.get_agent_schema(state.active_agent)
        try:
            self.context.governance_manager.validate_action(agent_schema, artifact)
        except GovernanceViolation as gv:
            logger.error(f"Governance violation: {gv.message}")
            return {"error": gv.to_dict(), "next_node": "END"}

        # 2️⃣ Evaluate stage exit
        exit_allowed = await self._should_exit_stage(state, artifact, state_ctx)
        if exit_allowed:
            next_stage = self._determine_next_stage(state, artifact, state_ctx)
            if not next_stage:
                logger.info("Terminal stage reached")
                return {"next_node": END}
            state.stage_name = next_stage

        # 3️⃣ Determine next agent
        next_agent = self._select_next_agent(state)
        if not next_agent:
            logger.warning("No eligible agent for next stage")
            return {"next_node": END}

        # 4️⃣ HITL detection
        hitl_state = self._check_hitl_requirement(state)
        if hitl_state:
            logger.info("HITL required")
            return {"hitl": to_storage(hitl_state), "next_node": "hitl_node"}

        # 5️⃣ Update agent context
        agent_ctx = self._get_or_create_agent_context(state, next_agent)
        state.active_agent = next_agent
        state.agents[next_agent] = to_storage(agent_ctx)

        # 6️⃣ Route execution
        route_node = "agent_planner" if agent_ctx.requires_planning else "agent_runner"
        logger.info(f"Routing execution to {route_node} for agent {next_agent}")

        return {
            "stage_name": state.stage_name,
            "active_agent": next_agent,
            "agents": state.agents,
            "next_node": route_node,
        }

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _get_current_artifact(self, state: StateSchema) -> Dict[str, Any]:
        agent_record = state.agents.get(state.active_agent)
        if agent_record:
            return to_agent_context(agent_record).control_raw
        return {}

    def _build_state_ctx(self, state: StateSchema) -> Dict[str, Any]:
        return {
            "task": state.task,
            "stage_name": state.stage_name,
            "data": state.data,
            "recent_tools": state.recent_tools,
            "workflow_metadata": state.workflow_metadata,
        }

    async def _should_exit_stage(
        self,
        state: StateSchema,
        artifact: dict,
        state_ctx: dict,
    ) -> bool:
        try:
            return self.context.stage_manager.evaluate_exit(state.stage_name, artifact, state_ctx)
        except Exception as e:
            logger.error(f"Stage exit evaluation failed: {e}")
            return False

    def _determine_next_stage(self, state: StateSchema, artifact: dict, state_ctx: dict) -> Optional[str]:
        allowed_stages = self.context.governance_manager.allowed_next_stages(
            state.stage_name, artifact, state_ctx
        )
        return allowed_stages[0] if allowed_stages else None

    def _select_next_agent(self, state: StateSchema) -> Optional[str]:
        allowed_agents = self.context.stage_manager.allowed_agents(state.stage_name)
        return self.context.agent_manager.first_agent(allowed_agents) if allowed_agents else None

    def _check_hitl_requirement(self, state: StateSchema) -> Optional[HITLState]:
        metadata = state.workflow_metadata or {}
        flags = metadata.get("hitl_flags", {})
        if flags.get("requires_approval"):
            return HITLState(stage_name=state.stage_name, agent_name=state.active_agent, reason="Approval required")
        if flags.get("abort_requested"):
            return HITLState(stage_name=state.stage_name, agent_name=state.active_agent, reason="Human abort requested")
        return None

    def _get_or_create_agent_context(self, state: StateSchema, agent_name: str):
        existing = state.agents.get(agent_name)
        if existing:
            return to_agent_context(existing)
        return self.context.agent_manager.create_agent_context(agent_name=agent_name, stage_name=state.stage_name)