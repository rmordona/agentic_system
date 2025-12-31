# runtime/workspace_loader.py

import json
import hashlib
from pathlib import Path
from agents.skills.agent import SkillAgent
from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
#from graph.state_graph import build_dynamic_graph
from runtime.logger import AgentLogger


class WorkspaceLoader:
    """
    Loads a workspace from disk, including all agent artifacts.
    Compiles LangGraph graph based on stage.json and registered agents.
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name
        
        self.version_hash = None

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(self.workspace_name, component="workspace_loader")

    # --------------------------------------------------
    # Load workspace.json configuration
    # Invoked from RuntimeManager
    # --------------------------------------------------

    def load_workspace(self) -> Dict[str, Any]:
        """
        Load and validate the workspace definition.
        This is the SINGLE entrypoint used by RuntimeManager.
        """
        workspace_file = self.workspace_path / "workspace.json"

        if not workspace_file.exists():
            raise FileNotFoundError(f"workspace.json not found in {self.workspace_path}")

        workspace_meta = self._load_json(workspace_file)

        # Optional: load tools.json, stages.json, etc
        workspace_meta["__path__"] = str(self.workspace_path)

        # Compute workspace version hash
        self.version_hash = self._compute_version_hash()

        logger.info("Workspace loaded successfully")
        return workspace_meta

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _load_json(self, path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

    def _compute_version_hash(self):
        h = hashlib.sha256()
        for file in sorted(self.workspace_path.rglob("*")):
            if file.is_file():
                h.update(file.read_bytes())
        return h.hexdigest()

