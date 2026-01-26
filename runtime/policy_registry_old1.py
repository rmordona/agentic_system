import ast
from typing import Any, Callable, Dict

from runtime.exit_condition_evaluator import ExitConditionEvaluator

################################################################################
# Policy Predicate - Old Implementation
################################################################################
class PolicyRegistry:

    VARIABLES = {
        "hitl_approved": False,
        "human_abort_confirmed": False,
    }

    def __init__(self):
        self._conditions = {}
        self.initialize()

    def register(self, name: str, fn: callable):
        self._conditions[name] = fn

    def get(self, name: str):
        if name not in self._conditions:
            raise KeyError(f"Exit condition '{name}' is not registered")
        return self._conditions[name]

    def evaluate(
        self,
        compiled_expr: ast.Expression,
        artifact: dict,
        state: dict | None = None,
    ) -> bool:
        return self.evaluator.evaluate(compiled_expr, artifact, state)

    def compile(self, expr: str) -> ast.Expression:
        return self.evaluator.compile(expr)

    def initialize(self):

        self.register(
            "artifact_is_valid",
            lambda artifact, state: artifact.is_valid()
        )

        self.register(
            "human_approved",
            lambda artifact, state: state.get("approved") is True
        )

        self.register(
            "all_proposals_reviewed",
            lambda artifact, state: all("status" in p for p in artifact.get("current_plan", []))
        )

        self.register(
            "accepted_proposals_exist",
            lambda artifact, state: any(
                p.get("status") == "accepted"
                for p in artifact.get("current_plan", [])
            )
        )

        self.register(
            "all_proposals_invalid",
            lambda artifact, state: (
                artifact.get("current_plan")
                and all(p.get("status") == "invalid" for p in artifact["current_plan"])
            )
        )

        self.register(
            "artifact_requires_new_ideas",
            lambda artifact, state: any(
                p.get("superseded", False)
                for p in artifact.get("current_plan", [])
            )
        )

        self.register(
            "critical_issues_detected",
            lambda artifact, state: any(
                p.get("conflict", False)
                for p in artifact.get("current_plan", [])
            )
        )

        self.register(
            "proposal_conflicts_with_spec",
            lambda artifact, state: artifact.get("conflicts_with_spec", False)
        )

        self.register(
            "artifact_has_spec_gaps",
            lambda artifact, state: artifact.get("spec_gaps", False)
        )

        self.register(
            "clarifications_resolved",
            lambda artifact, state: artifact.get("clarifications_resolved", False)
        )

        self.register(
            "clarification_failed",
            lambda artifact, state: artifact.get("clarification_failed", False)
        )

        self.evaluator = ExitConditionEvaluator(self._conditions, self.VARIABLES)


