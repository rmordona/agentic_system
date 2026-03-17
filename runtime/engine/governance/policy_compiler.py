from __future__ import annotations
from typing import Dict, Any

from runtime.logger import AgentLogger
from runtime.engine.policy.policy_registry import PolicyRegistry
from runtime.engine.governance.governance_graph import GovernanceGraph, GovernanceEdge

logger = AgentLogger.get_logger(component="system")


class PolicyCompiler:
    """
    Compiles declarative governance policy into a runtime GovernanceGraph.

    Responsibilities
    ----------------
    - parse transition logic
    - compile predicates using PolicyRegistry
    - build deterministic governance graph
    """

    def __init__(self, policy_registry: PolicyRegistry):
        self.policy_registry = policy_registry

    def compile(self, policy_data: Dict[str, Any]) -> GovernanceGraph:

        logger.info("Compiling governance policy into graph")

        graph = GovernanceGraph()

        for stage_name, stage_policy in policy_data.items():

            graph.register_node(stage_name)

            transitions = stage_policy.get("transition_logic", [])

            for transition in transitions:

                predicate_expr = transition.get("if")
                target = transition.get("allow")

                compiled = None

                if predicate_expr:
                    compiled = self.policy_registry.compile(predicate_expr)

                edge = GovernanceEdge(
                    source_stage=stage_name,
                    target_stage=target,
                    predicate=compiled,
                    description=predicate_expr,
                )

                graph.register_edge(edge)

                logger.info(
                    f"Registered transition: {stage_name} → {target} "
                    f"[{predicate_expr or 'always'}]"
                )

        logger.info("Governance policy compilation complete")

        return graph
