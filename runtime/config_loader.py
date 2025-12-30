# runtime/config_loader.py

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
import hashlib


class ConfigLoader:
    """
    Loads and merges runtime configuration.

    Priority (lowest → highest):
      1. Global config.json
      2. Workspace config.json
    """

    def __init__(
        self,
        global_config_path: Path,
        workspaces_root: Path | None = None,
    ):
        self.global_config_path = global_config_path
        self.workspaces_root = workspaces_root
        self._config: Dict[str, Any] = {}
        self._config_hash: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        """
        Load and merge config.json files.
        """
        if not self.global_config_path.exists():
            raise FileNotFoundError(f"Global config not found: {self.global_config_path}")

        global_config = self._load_json(self.global_config_path)

        workspace_config = {}
        if self.workspaces_root:
            ws_config_path = self.workspaces_root / "config.json"
            if ws_config_path.exists():
                workspace_config = self._load_json(ws_config_path)

        self._config = self._deep_merge(global_config, workspace_config)
        self._config_hash = self._compute_hash(self._config)
        return self._config

    def get(self) -> Dict[str, Any]:
        if not self._config:
            raise RuntimeError("Config not loaded yet")
        return self._config

    def get_hash(self) -> str:
        if not self._config_hash:
            raise RuntimeError("Config not loaded yet")
        return self._config_hash

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_json(self, path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two dictionaries.
        override wins over base.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """
        Deterministic hash for reload detection.
        """
        canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

