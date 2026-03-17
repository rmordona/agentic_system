from __future__ import annotations
from typing import Dict, Any, List

from runtime.logger import AgentLogger
from runtime.engine.policy.policy_registry import PolicyRegistry
from runtime.engine.governance.governance_graph import GovernanceGraph

logger = AgentLogger.get_logger(component="system")


class GovernanceEngine:
    """
    Runtime policy evaluation engine.

    Responsibilities
    ----------------
    - determine allowed next stages
    - enforce stage transition policies
    - provide audit visibility
    """

    def __init__(
        self,
        graph: GovernanceGraph,
        policy_registry: PolicyRegistry,
    ):
        self.graph = graph
        self.policy_registry = policy_registry

    def next_allowed_stages(
        self,
        current_stage: str,
        artifact: dict,
        state_ctx: dict,
    ) -> List[str]:

        logger.info(f"Evaluating governance transitions from stage '{current_stage}'")

        allowed = self.graph.next_stages(
            current_stage=current_stage,
            policy_registry=self.policy_registry,
            artifact=artifact,
            state_ctx=state_ctx,
        )

        logger.info(f"Allowed next stages: {allowed}")

        return allowed

    def must_block(
        self,
        current_stage: str,
        artifact: dict,
        state_ctx: dict,
    ) -> bool:

        allowed = self.next_allowed_stages(current_stage, artifact, state_ctx)

        if not allowed:
            logger.warning(
                f"No transitions allowed from stage '{current_stage}'. Blocking workflow."
            )
            return True

        return False
