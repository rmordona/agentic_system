from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import ast

from runtime.logger import AgentLogger
from runtime.engine.policy.policy_registry import PolicyRegistry

logger = AgentLogger.get_logger(component="system")


###############################################################################
# Governance Edge
###############################################################################

@dataclass(frozen=True)
class GovernanceEdge:
    """
    Represents a transition between stages guarded by a compiled predicate.
    """

    source_stage: str
    target_stage: str
    predicate: Optional[ast.Expression] = None
    description: Optional[str] = None

    def evaluate(
        self,
        policy_registry: PolicyRegistry,
        artifact: dict,
        state_ctx: dict,
    ) -> bool:

        if self.predicate is None:
            return True

        try:
            return policy_registry.evaluate(
                compiled_expr=self.predicate,
                artifact=artifact,
                state_ctx=state_ctx,
            )
        except Exception as e:
            logger.error(
                f"Policy evaluation failed for edge "
                f"{self.source_stage} → {self.target_stage}: {e}"
            )
            return False


###############################################################################
# Governance Node
###############################################################################

@dataclass
class GovernanceNode:
    """
    Node representing a stage checkpoint in the governance graph.
    """

    stage_name: str
    edges: List[GovernanceEdge] = field(default_factory=list)

    def add_edge(self, edge: GovernanceEdge):
        self.edges.append(edge)


###############################################################################
# Governance Graph
###############################################################################

class GovernanceGraph:
    """
    Immutable stage transition graph compiled from governance policy.

    Each stage becomes a node and each transition rule becomes an edge.
    """

    def __init__(self):
        self.nodes: Dict[str, GovernanceNode] = {}

    def register_node(self, stage_name: str):

        if stage_name not in self.nodes:
            self.nodes[stage_name] = GovernanceNode(stage_name)

    def register_edge(self, edge: GovernanceEdge):

        if edge.source_stage not in self.nodes:
            self.register_node(edge.source_stage)

        if edge.target_stage not in self.nodes:
            self.register_node(edge.target_stage)

        self.nodes[edge.source_stage].add_edge(edge)

    def next_stages(
        self,
        current_stage: str,
        policy_registry: PolicyRegistry,
        artifact: dict,
        state_ctx: dict,
    ) -> List[str]:

        node = self.nodes.get(current_stage)

        if not node:
            logger.warning(f"Stage '{current_stage}' not found in governance graph")
            return []

        allowed: List[str] = []

        for edge in node.edges:

            if edge.evaluate(policy_registry, artifact, state_ctx):
                allowed.append(edge.target_stage)

        return allowed

    def list_stages(self) -> List[str]:
        return list(self.nodes.keys())

    def describe(self) -> Dict[str, Any]:

        summary = {}

        for stage, node in self.nodes.items():
            summary[stage] = [
                {
                    "target": edge.target_stage,
                    "predicate": str(edge.predicate) if edge.predicate else "always"
                }
                for edge in node.edges
            ]

        return summary
