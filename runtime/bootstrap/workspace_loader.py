from __future__ import annotations
from __future__ import annotations
from core.paths import WORKSPACES_ROOT

import json
import hashlib
from pathlib import Path
from typing import Any, Dict

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class WorkspaceLoader:
    """
    Loads a workspace from disk, including all agent artifacts.
    Compiles LangGraph graph based on stage.json and registered agents.
    """

    def __init__(self, workspace_name: str):

        self.workspace_path = WORKSPACES_ROOT / workspace_name
        self.version_hash = None

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
        logger.info(f"Loading workspace profile: {workspace_file}")

        if not workspace_file.exists():
            raise FileNotFoundError(f"workspace.json not found in {self.workspace_path}")

        workspace_meta = self._load_json(workspace_file)

        # Optional: load tools.json, stages.json, etc
        workspace_meta["__path__"] = str(self.workspace_path)

        # Compute workspace version hash
        self.version_hash = self._compute_version_hash()

        logger.info(f"Workspace Meta: {workspace_meta}")
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

