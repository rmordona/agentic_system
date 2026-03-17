# runtime/engine/stage/stage_registry.py

from __future__ import annotations
from typing import Dict, List, Optional, Any

from runtime.logger import AgentLogger
from runtime.engine.stage.stage_schema import StageSchema

logger = AgentLogger.get_logger(component="system")


class StageRegistry:
    """
    Immutable registry of all governance stages.

    Responsibilities:
    - Store StageSchema objects
    - Provide stage lookup utilities
    - Track entry stage
    - Provide diagnostic information
    """

    def __init__(self):

        self._stages: Dict[str, StageSchema] = {}
        self._entry_stage: Optional[str] = None

    # ---------------------------------------------------------
    # Registration
    # ---------------------------------------------------------

    def register_stage(
        self,
        stage: StageSchema,
        entry: bool = False,
    ) -> None:

        if stage.name in self._stages:
            raise ValueError(
                f"Duplicate stage registration: {stage.name}"
            )

        logger.info(f"Registering stage: {stage.name}")

        self._stages[stage.name] = stage

        if entry or not self._entry_stage:
            self._entry_stage = stage.name

    # ---------------------------------------------------------
    # Lookup
    # ---------------------------------------------------------

    def get_stage(self, name: str) -> Optional[StageSchema]:
        return self._stages.get(name)

    def require_stage(self, name: str) -> StageSchema:
        """
        Safe stage lookup that throws if the stage does not exist.
        """

        stage = self._stages.get(name)

        if not stage:
            raise KeyError(f"Unknown stage: {name}")

        return stage

    def list_stages(self) -> List[str]:
        return list(self._stages.keys())

    def stage_exists(self, name: str) -> bool:
        return name in self._stages

    # ---------------------------------------------------------
    # Entry Stage
    # ---------------------------------------------------------

    def get_entry_stage(self) -> str:

        if not self._entry_stage:
            raise RuntimeError(
                "No entry stage defined in governance policy"
            )

        return self._entry_stage

    # ---------------------------------------------------------
    # Stage Properties
    # ---------------------------------------------------------

    def is_terminal(self, stage_name: str) -> bool:

        stage = self.require_stage(stage_name)

        return stage.terminal

    def allowed_agents(self, stage_name: str) -> List[str]:

        stage = self.require_stage(stage_name)

        return stage.allowed_agents

    def get_terminal_stages(self) -> List[str]:

        return [
            name
            for name, stage in self._stages.items()
            if stage.terminal
        ]

    # ---------------------------------------------------------
    # Diagnostics
    # ---------------------------------------------------------

    def describe(self) -> Dict[str, Any]:

        stages = {}

        for name, stage in self._stages.items():

            stages[name] = stage.to_dict()

        return {
            "entry_stage": self._entry_stage,
            "stage_count": len(self._stages),
            "stages": stages,
        }