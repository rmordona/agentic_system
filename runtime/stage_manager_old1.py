from __future__ import annotations
from core.paths import WORKSPACES_ROOT

import re
from pathlib import Path
from typing import Dict, List, Optional

from runtime.logger import AgentLogger
from runtime.stage.stage_schema import StageSchema
from runtime.engine.governance.policy_registry import PolicyRegistry

logger = AgentLogger.get_logger(component="system")


###############################################################################
# Stage Manager
###############################################################################
class StageManager:
    """
    StageManager loads and manages governance stages for a workspace.

    Responsibilities
    ----------------
    - Parse governance_policy.md
    - Register StageSchema objects
    - Compile stage exit predicates
    - Expose allowed agents per stage
    - Provide entry stage for workflow bootstrap
    - Provide stage lookup utilities

    Important
    ----------
    Stages represent **policy checkpoints**, not pipeline steps.
    """

    POLICY_FILE = "governance_policy.md"

    def __init__(self, workspace_name: str):

        self.workspace_name = workspace_name
        self.workspace_path = WORKSPACES_ROOT / workspace_name

        self.policy_path = self.workspace_path / self.POLICY_FILE

        self._stages: Dict[str, StageSchema] = {}

        self._entry_stage: Optional[str] = None

        self._compiled_exit_conditions: Dict[str, List] = {}

        self.policy_registry: Optional[PolicyRegistry] = None

    # -------------------------------------------------------------------------
    # Register Stages
    # -------------------------------------------------------------------------
    def register_stages(self):

        logger.info(f"Loading governance policy: {self.policy_path}")

        if not self.policy_path.exists():
            raise FileNotFoundError(
                f"Governance policy not found: {self.policy_path}"
            )

        self.policy_registry = PolicyRegistry(self.workspace_path)

        text = self.policy_path.read_text()

        stage_blocks = self._extract_stage_blocks(text)

        for block in stage_blocks:

            schema, exit_conditions = self._parse_stage(block)

            self._stages[schema.name] = schema

            compiled = []
            for expr in exit_conditions:
                compiled.append(self.policy_registry.compile(expr))

            self._compiled_exit_conditions[schema.name] = compiled

            logger.info(f"Registered stage: {schema.name}")

        if not self._stages:
            raise RuntimeError("No stages discovered in governance policy")

        # First stage becomes entry stage
        self._entry_stage = list(self._stages.keys())[0]

        logger.info(f"Entry stage set to: {self._entry_stage}")

    # -------------------------------------------------------------------------
    # Extract Stage Blocks
    # -------------------------------------------------------------------------
    def _extract_stage_blocks(self, text: str) -> List[str]:

        pattern = r"##\s*Stage:\s*.*?(?=##\s*Stage:|\Z)"

        matches = re.findall(pattern, text, flags=re.DOTALL)

        return matches

    # -------------------------------------------------------------------------
    # Parse Stage
    # -------------------------------------------------------------------------
    def _parse_stage(self, block: str):

        name_match = re.search(r"##\s*Stage:\s*(.*)", block)

        if not name_match:
            raise ValueError("Stage name not found")

        name = name_match.group(1).strip()

        description_match = re.search(r"\*\*Description\*\*:\s*(.*)", block)

        description = description_match.group(1).strip() if description_match else ""

        agents_match = re.search(r"\*\*Required Agents\*\*:\s*\[(.*?)\]", block)

        allowed_agents = []

        if agents_match:
            allowed_agents = [
                a.strip().replace('"', "").replace("'", "")
                for a in agents_match.group(1).split(",")
            ]

        terminal = "terminal" in block.lower()

        exit_conditions = self._extract_exit_conditions(block)

        schema = StageSchema(
            name=name,
            description=description,
            allowed_agents=allowed_agents,
            terminal=terminal,
        )

        return schema, exit_conditions

    # -------------------------------------------------------------------------
    # Extract Exit Conditions
    # -------------------------------------------------------------------------
    def _extract_exit_conditions(self, block: str) -> List[str]:

        results = []

        lines = block.split("\n")

        for line in lines:

            if line.strip().startswith("- `") and "`" in line:

                expr = line.strip().strip("- ").strip("`")

                results.append(expr)

        return results

    # -------------------------------------------------------------------------
    # Entry Stage
    # -------------------------------------------------------------------------
    def get_entry_stage(self) -> str:

        if not self._entry_stage:
            raise RuntimeError("StageManager not initialized")

        return self._entry_stage

    # -------------------------------------------------------------------------
    # Stage Lookup
    # -------------------------------------------------------------------------
    def get_stage(self, stage_name: str) -> Optional[StageSchema]:

        return self._stages.get(stage_name)

    def stage_exists(self, stage_name: str) -> bool:

        return stage_name in self._stages

    def list_stages(self) -> List[str]:

        return list(self._stages.keys())

    # -------------------------------------------------------------------------
    # Allowed Agents
    # -------------------------------------------------------------------------
    def allowed_agents(self, stage_name: str) -> List[str]:

        schema = self._stages.get(stage_name)

        if not schema:
            logger.warning(f"Unknown stage: {stage_name}")
            return []

        return schema.allowed_agents

    # -------------------------------------------------------------------------
    # Terminal Check
    # -------------------------------------------------------------------------
    def is_terminal(self, stage_name: str) -> bool:

        schema = self._stages.get(stage_name)

        if not schema:
            return False

        return schema.terminal

    # -------------------------------------------------------------------------
    # Exit Conditions
    # -------------------------------------------------------------------------
    def exit_conditions(self, stage_name: str):

        return self._compiled_exit_conditions.get(stage_name, [])

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------
    def describe(self) -> Dict:

        return {
            "workspace": self.workspace_name,
            "entry_stage": self._entry_stage,
            "stages": {
                name: schema.to_dict()
                for name, schema in self._stages.items()
            },
        }