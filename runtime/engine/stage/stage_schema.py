# runtime/engine/stage/stage_schema.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Any, Dict, Optional, Callable

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


@dataclass(frozen=True)
class StageTransition:
    predicate: Any
    target: str
    description: Optional[str] = None
    condition_text: Optional[str] = None


@dataclass(frozen=True)
class StageSchema:
    """
    Immutable governance stage definition.

    Responsibilities:
    - Define stage contract
    - Evaluate entry/exit conditions
    - Resolve stage transitions
    """

    name: str
    description: str
    policy_type: str

    allowed_agents: List[str] = field(default_factory=list)

    entry_conditions: List[Any] = field(default_factory=list)
    exit_conditions: List[Any] = field(default_factory=list)

    transitions: List[StageTransition]  = field(default_factory=list)

    supported_intents: List[Any] = field(default_factory=list)

    terminal: bool = False
    priority: int = 1

    intents: List[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "policy_type": self.policy_type,
            "description": self.description,
            "allowed_agents": self.allowed_agents,
            "terminal": self.terminal,
            "priority": self.priority,
            "entry_conditions": len(self.entry_conditions),
            "exit_conditions": len(self.exit_conditions),
            "transitions": [
                {
                    "target": t.target,
                    "description": t.description,
                    "condition_text": t.condition_text
                }
                for t in self.transitions
            ],
            "intents": self.intents,
            "audit" : self.audit,
        }

    # ---------------------------------------------------------
    # Agent Authorization
    # ---------------------------------------------------------

    def allows_agent(self, agent_name: str) -> bool:
        return agent_name in self.allowed_agents

    # ---------------------------------------------------------
    # Governance Evaluation
    # ---------------------------------------------------------

    def can_enter(
        self,
        evaluator: Callable,
        ctx_obj: Any,
        artifact: Dict,
    ) -> bool:

        return self._evaluate_conditions(
            self.entry_conditions,
            evaluator,
            ctx_obj,
            artifact,
        )

    def can_exit(
        self,
        evaluator: Callable,
        ctx_obj: Any,
        artifact: Dict,
    ) -> bool:

        return self._evaluate_conditions(
            self.exit_conditions,
            evaluator,
            ctx_obj,
            artifact,
        )

    def resolve_transition(
        self,
        evaluator: Callable,
        ctx_obj: Any,
        artifact: Dict,
    ) -> Optional[str]:

        for transition in self.transitions:

            condition = transition.get("predicate")
            target = transition.get("target")

            try:

                if evaluator(condition, artifact, ctx_obj):
                    return target

            except Exception as e:

                logger.error(
                    f"Transition evaluation failed in stage '{self.name}': {e}"
                )

        return None

    # ---------------------------------------------------------
    # Internal Helpers
    # ---------------------------------------------------------

    def _evaluate_conditions(
        self,
        conditions,
        evaluator,
        ctx_obj,
        artifact,
    ) -> bool:

        if not conditions:
            return True

        try:

            for cond in conditions:

                if not evaluator(cond, artifact, ctx_obj):
                    return False

            return True

        except Exception as e:

            logger.error(
                f"Condition evaluation failed in stage '{self.name}': {e}"
            )

            return False