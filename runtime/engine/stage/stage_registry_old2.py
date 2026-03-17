from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any

from runtime.logger import AgentLogger
from runtime.engine.stage.stage_schema import StageSchema

logger = AgentLogger.get_logger(component="system")


class StageRegistry:
    """
    Immutable registry of all stages within a governance execution policy.
    """

    def __init__(self):

        self._stages: Dict[str, StageSchema] = {}
        self._exit_conditions: Dict[str, List] = {}
        self._entry_conditions: Dict[str, List] = {}
        self._transitions: Dict[str, List[Tuple[Any, str]]] = {}

        self._entry_stage: Optional[str] = None

    # ----------------------------------------------------------
    # Registration
    # ----------------------------------------------------------

    def register_stage(
        self,
        stage: StageSchema,
        entry_conditions: List,
        exit_conditions: List,
        transitions: List[Tuple[Any, str]],
        entry: bool = False,
    ) -> None:

        name = stage.name

        if name in self._stages:
            raise ValueError(f"Duplicate stage registration: {name}")

        logger.info(f"Registering stage: {name}")

        self._stages[name] = stage
        self._entry_conditions[name] = entry_conditions
        self._exit_conditions[name] = exit_conditions
        self._transitions[name] = transitions

        if entry or not self._entry_stage:
            self._entry_stage = name

    # ----------------------------------------------------------
    # Lookup Utilities
    # ----------------------------------------------------------

    def get_stage(self, name: str) -> Optional[StageSchema]:
        return self._stages.get(name)

    def list_stages(self) -> List[str]:
        return list(self._stages.keys())

    def stage_exists(self, name: str) -> bool:
        return name in self._stages

    def get_entry_stage(self) -> str:

        if not self._entry_stage:
            raise RuntimeError("No entry stage defined in governance policy")

        return self._entry_stage

    def allowed_agents(self, stage_name: str) -> List[str]:

        stage = self._stages.get(stage_name)

        if not stage:
            logger.warning(f"Unknown stage requested: {stage_name}")
            return []

        return stage.allowed_agents

    def is_terminal(self, stage_name: str) -> bool:

        stage = self._stages.get(stage_name)

        if not stage:
            return False

        return stage.terminal

    def entry_conditions(self, stage_name: str):
        return self._entry_conditions.get(stage_name, [])

    def exit_conditions(self, stage_name: str):
        return self._exit_conditions.get(stage_name, [])

    def get_transitions(self, stage_name: str):
        return self._transitions.get(stage_name, [])

    # ----------------------------------------------------------
    # Diagnostics
    # ----------------------------------------------------------

    def describe(self) -> Dict[str, Any]:

        return {
            "entry_stage": self._entry_stage,
            "stages": {
                name: stage.to_dict()
                for name, stage in self._stages.items()
            },
        }