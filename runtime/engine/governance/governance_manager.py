from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from runtime.engine.policy.policy_registry import PolicyRegistry
from runtime.engine.governance.governance_engine import GovernanceEngine
from runtime.agent_profiler import AgentProfile
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class GovernanceViolation(Exception):
    """Raised when an Agent's action or output violates domain/system policies."""

    def __init__(self, rule_id: str, message: str, offending_data: Any = None):
        self.rule_id = rule_id
        self.message = message
        self.offending_data = offending_data
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": "GovernanceViolation",
            "rule_id": self.rule_id,
            "message": self.message,
            "data": self.offending_data,
        }


class GovernanceManager:
    def __init__(
        self,
        engine: GovernanceEngine,
        policy_registry: PolicyRegistry
    ):
        self.engine = engine
        self.policy_registry = policy_registry


    def validate_action(
        self,
        profile: AgentProfile,
        artifact: dict
    ):
        """
        Enforce agent capability and authority constraints.
        """

        # -------------------------------------------------
        # Forbidden actions
        # -------------------------------------------------
        for action in profile.forbidden_actions:
            if action in artifact:
                raise GovernanceViolation(
                    rule_id="forbidden_action",
                    message=f"Agent attempted forbidden action: {action}",
                    offending_data=artifact.get(action)
                )

        # -------------------------------------------------
        # Expected outputs
        # -------------------------------------------------
        for output in profile.expected_outputs:
            if output not in artifact:
                raise GovernanceViolation(
                    rule_id="missing_output",
                    message=f"Expected output missing: {output}",
                )

        # -------------------------------------------------
        # Max iteration enforcement
        # -------------------------------------------------
        iteration = artifact.get("iteration")

        if profile.max_iterations and iteration:
            if iteration > profile.max_iterations:
                raise GovernanceViolation(
                    rule_id="iteration_limit",
                    message="Agent exceeded maximum iterations"
                )

        # -------------------------------------------------
        # HITL requirement
        # -------------------------------------------------
        if profile.requires_human_approval:
            artifact["requires_hitl"] = True

    def allowed_next_stages(
        self,
        current_stage: str,
        artifact: dict,
        state_ctx: dict,
    ) -> List[str]:
        """
        Query the GovernanceEngine to return allowed next stages.
        """
        return self.engine.next_allowed_stages(
            current_stage=current_stage,
            artifact=artifact,
            state_ctx=state_ctx,
        )

    def must_block(
        self,
        current_stage: str,
        artifact: dict,
        state_ctx: dict,
    ) -> bool:
        """
        Determines if workflow should be blocked (no allowed transitions).
        """
        allowed = self.allowed_next_stages(current_stage, artifact, state_ctx)
        if not allowed:
            logger.warning(
                f"No transitions allowed from stage '{current_stage}'. Blocking workflow."
            )
            return True
        return False
