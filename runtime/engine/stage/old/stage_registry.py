from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from runtime.logger import AgentLogger
from runtime.stage.stage_schema import StageSchema
from core.paths import WORKSPACES_ROOT

logger = AgentLogger.get_logger(component="system")


###############################################################################
# Stage Registry
###############################################################################

class StageRegistry:
    """
    Central registry of stage schemas for a workspace.

    Responsibilities
    ----------------
    • load stage definitions
    • validate stage contracts
    • expose allowed agents
    • expose entry stage
    • provide lookup utilities

    The registry contains **no transition logic**.
    Transition policies are handled by GovernanceGraph.
    """

    def __init__(self, workspace_name: str):

        self.workspace_name = workspace_name
        self.workspace_path = WORKSPACES_ROOT / workspace_name

        self._stages: Dict[str, StageSchema] = {}

        self._entry_stage: Optional[str] = None

        self._all_agents: List[str] = []

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------

    def load(self, stage_data: Dict[str, Any]):

        logger.info(f"Loading stage registry for workspace '{self.workspace_name}'")

        stages = stage_data.get("stages", [])

        if not stages:
            raise ValueError("No stages defined in workspace configuration")

        for stage_meta in stages:

            schema = self._build_schema(stage_meta)

            if schema.name in self._stages:
                raise ValueError(f"Duplicate stage detected: {schema.name}")

            self._stages[schema.name] = schema

            for agent in schema.allowed_agents:
                if agent not in self._all_agents:
                    self._all_agents.append(agent)

            logger.info(f"Registered stage: {schema.name}")

        self._entry_stage = stage_data.get("entry_stage")

        if not self._entry_stage:
            raise ValueError("Workspace must define an entry_stage")

        if self._entry_stage not in self._stages:
            raise ValueError(
                f"Entry stage '{self._entry_stage}' not defined in stages"
            )

        logger.info(f"Entry stage set to '{self._entry_stage}'")

    # -------------------------------------------------------------------------
    # Schema Builder
    # -------------------------------------------------------------------------

    def _build_schema(self, meta: Dict[str, Any]) -> StageSchema:

        try:

            return StageSchema(
                name=meta["name"],
                description=meta.get("description", ""),
                allowed_agents=meta.get("allowed_agents", []),
                priority=meta.get("priority", 1),
                terminal=meta.get("terminal", False),
                metadata=meta.get("metadata", {}),
            )

        except Exception as e:

            logger.error(f"Failed to build stage schema: {meta}")
            raise e

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get(self, stage_name: str) -> Optional[StageSchema]:

        return self._stages.get(stage_name)

    def exists(self, stage_name: str) -> bool:

        return stage_name in self._stages

    def list_stages(self) -> List[str]:

        return list(self._stages.keys())

    def entry_stage(self) -> str:

        return self._entry_stage

    # -------------------------------------------------------------------------
    # Agent access
    # -------------------------------------------------------------------------

    def allowed_agents(self, stage_name: str) -> List[str]:

        schema = self.get(stage_name)

        if not schema:
            logger.warning(f"Stage '{stage_name}' not found")

            return []

        return schema.allowed_agents

    def all_agents(self) -> List[str]:

        return list(self._all_agents)

    # -------------------------------------------------------------------------
    # Terminal
    # -------------------------------------------------------------------------

    def is_terminal(self, stage_name: str) -> bool:

        schema = self.get(stage_name)

        if not schema:
            return False

        return schema.terminal

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def describe(self) -> Dict[str, Any]:

        return {
            "workspace": self.workspace_name,
            "entry_stage": self._entry_stage,
            "stages": {
                name: schema.to_dict()
                for name, schema in self._stages.items()
            },
        }
