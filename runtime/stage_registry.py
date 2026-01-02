"""
StageRegistry loads and validates stage definitions for a workspace.

It defines stage ordering, allowed agents, and exit conditions used by
the StageGraph during execution.

StageRegistry does NOT execute agents or manage state.
"""


from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from runtime.logger import AgentLogger
from events.event_bus import EventBus

class Stage:
    def __init__(self, meta: Dict[str, Any], workspace_name: str, exit_condition: Optional[Callable[[Dict[str, Any]], bool]] = None):
        self.name: str = meta["name"]
        self.allowed_agents: List[str] = meta.get("allowed_agents", [])
        self.next_stages: List[str] = meta.get("next_stages", [])
        self.priority: int = meta.get("priority", 1)
        self.terminal: bool = meta.get("terminal", False)

        # Exit condition can be a string expression or callable
        raw_exit = meta.get("exit_condition", "False")
        self.exit_condition: Callable[[dict], bool] = exit_condition or self._compile_exit_condition(raw_exit)

        self.event_bus = None

        # Logger
        self.logger = AgentLogger.get_logger(workspace_name, component=f"stage_{self.name}")

        assert callable(self.exit_condition), "exit_condition must be callable"

    def _compile_exit_condition(self, expr: str) -> Callable[[dict], bool]:
        safe_globals = {"__builtins__": {"len": len, "any": any, "all": all, "sum": sum, "min": min, "max": max}}
        try:
            code = compile(expr, "<exit_condition>", "eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid exit_condition for stage '{self.name}': {expr}") from e

        def _exit_fn(state: dict) -> bool:
            return bool(eval(code, safe_globals, {"state": state}))

        return _exit_fn

    def should_exit(self, state: dict) -> bool:
        try:
            return self.exit_condition(state)
        except Exception as e:
            self.logger.error(f"Error evaluating exit_condition for stage '{self.name}': {e}")
            return False

    def __repr__(self) -> str:
        return f"Stage(name={self.name}, allowed_agents={self.allowed_agents})"

class StageRegistry:
    stage_file: str = "stage.json"

    def __init__(self, workspace_dir: Path, stage_file: Optional[Path] = None):
        self.workspace_dir = workspace_dir
        self.workspace_name = workspace_dir.name
        if stage_file is not None:
            self.stage_file = stage_file

        self._stages: Dict[str, Stage] = {}
        self._order: List[str] = []
        self.logger = AgentLogger.get_logger(self.workspace_name, component="stage_registry")

    def load_stages(self):
        stage_path = Path(self.workspace_dir / self.stage_file)
        if not stage_path.exists():
            self.logger.error(f"Stage file not found: {stage_path}")
            raise FileNotFoundError(f"Stage file not found: {stage_path}")

        with stage_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        stages_meta = data.get("stages", [])
        if not stages_meta:
            self.logger.warning("No stages defined in stage.json")
            return

        # Sort by priority
        sorted_stages = sorted(stages_meta, key=lambda s: s.get("priority", 1))
        for stage_meta in sorted_stages:
            stage = Stage(stage_meta, self.workspace_name)
            self._stages[stage.name] = stage
            self._order.append(stage.name)
            self.logger.info(f"Registered stage '{stage.name}' with allowed_agents={stage.allowed_agents}")

    # -----------------------------
    # Accessors
    # -----------------------------
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
            self.logger.warning(f"Current stage '{current_stage}' not found in stage order")
            return None
        idx = self._order.index(current_stage)
        if idx + 1 < len(self._order):
            return self._order[idx + 1]
        return None

    def allowed_agents(self, stage_name: str) -> List[str]:
        stage = self.get(stage_name)
        return stage.allowed_agents if stage else []

    def is_terminal(self, stage_name: str) -> bool:
        stage = self.get(stage_name)
        return stage.terminal if stage else False
