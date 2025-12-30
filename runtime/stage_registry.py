from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from runtime.logger import AgentLogger

class Stage:
    """
    Represents a single stage in the workflow.
    """

    def __init__(self, meta: Dict[str, Any], workspace_name: str):
        self.name: str = meta["name"]
        self.allowed_agents: List[str] = meta.get("allowed_agents", [])
        self.exit_condition: str = meta.get("exit_condition", "False")
        self.next_stages: List[str] = meta.get("next_stages", [])
        self.priority: int = meta.get("priority", 1)
        self.terminal: bool = meta.get("terminal", False)

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(workspace_name, component=f"stage_{self.name}")

    def should_exit(self, state: Dict[str, Any]) -> bool:
        """
        Evaluates the exit_condition in the context of the current state.
        Warning: uses eval, ensure stage.json is trusted.
        """
        try:
            return bool(eval(self.exit_condition, {}, {"state": state}))
        except Exception as e:
            logger.error(f"Error evaluating exit_condition for stage '{self.name}': {e}")
            return False


class StageRegistry:
    """
    Loads and manages all stages from a workspace stage.json.
    Provides helper methods for stage ordering and agent gating.
    """

    # Logger for StageRegistry
    logger = None

    stage_file: str = "stage.json"

    def __init__(self, workspace_dir: Path, stage_file: Optional[Path] = None):
        """
        stage_file: path to stage.json
        """
        self.workspace_dir = workspace_dir
        self.workspace_name = workspace_dir.name

        if stage_file is not None:
            self.stage_file = stage_file

        self._stages: Dict[str, Stage] = {}
        self._order: List[str] = []

        print(f"workspace dir: {self.workspace_dir}")
        print(f"workspace_name: {self.workspace_name}")
        print(f"stage_file : {self.stage_file}")

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(self.workspace_name, component="stage_registry")

    # ------------------------------------------------------------------
    # Loading and Parsing
    # ------------------------------------------------------------------

    def load_stages(self):
        if not self.stage_file:
            logger.error("Stage file path not set")
            raise ValueError("Stage file path not set")

        stage_path = Path(self.workspace_dir / self.stage_file)  # convert str → Path

        if not stage_path.exists():
            logger.error(f"Stage file not found: {stage_path}")
            raise FileNotFoundError(f"Stage file not found: {stage_path}")

        # Open and read JSON
        with stage_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        stages_meta = data.get("stages", [])
        if not stages_meta:
            logger.warning("No stages defined in stage.json")
            return

        # Sort stages by priority (ascending)
        sorted_stages = sorted(stages_meta, key=lambda s: s.get("priority", 1))
    
        for stage_meta in sorted_stages:
            stage = Stage(stage_meta, self.workspace_name)
            self._stages[stage.name] = stage
            self._order.append(stage.name)
            logger.info(f"Registered stage '{stage.name}' with allowed_agents={stage.allowed_agents}")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, stage_name: str) -> Optional[Stage]:
        return self._stages.get(stage_name)

    def list_stages(self) -> List[str]:
        return list(self._stages.keys())

    def first_stage(self) -> str:
        if not self._order:
            raise ValueError("No stages loaded")
        return self._order[0]

    def next_stage(self, current_stage: str) -> Optional[str]:
        if current_stage not in self._order:
            logger.warning(f"Current stage '{current_stage}' not found in stage order")
            return None
        idx = self._order.index(current_stage)
        if idx + 1 < len(self._order):
            return self._order[idx + 1]
        return None

    def is_terminal(self, stage_name: str) -> bool:
        stage = self.get(stage_name)
        return stage.terminal if stage else False

    def allowed_agents(self, stage_name: str) -> List[str]:
        stage = self.get(stage_name)
        return stage.allowed_agents if stage else []

