# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/logger.py
#
# Description:
#   AgentLogger is a global, static logging facility.
#   Log routing is determined strictly by the `component` argument:
#
#     - component="system"  → logs/system.log
#     - component="runtime" → logs/runtime/<workspace>.log
#
#   No other routing logic is applied.
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-02
# -----------------------------------------------------------------------------

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from runtime.bootstrap.config_loader import ConfigLoader


class AgentLogger:
    """
    Global static logger.
    """

    _initialized: bool = False
    _loggers: Dict[str, logging.Logger] = {}
    _base_dir: Path | None = None
    _level: int = logging.INFO

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    @classmethod
    def initialize(cls) -> None:
        if cls._initialized:
            return

        runtime_dir = Path(__file__).parent
        root_dir = runtime_dir.parent

        config_path = runtime_dir / "bootstrap" / "config.json"
        workspaces_root = root_dir / "workspaces"

        config = ConfigLoader(
            global_config_path=config_path,
            workspaces_root=workspaces_root,
        ).load()

        logging_cfg = config.get("logging", {})
        base_dir = logging_cfg.get("base_dir", "logs")
        level_str = logging_cfg.get("level", "INFO")

        cls._base_dir = root_dir / base_dir
        cls._base_dir.mkdir(parents=True, exist_ok=True)

        cls._level = cls._parse_log_level(level_str)

        logging.basicConfig(level=cls._level)
        cls._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def get_logger(
        cls,
        component: str,
        workspace: Optional[str] = None,
    ) -> logging.Logger:
        """
        component must be either:
          - "system"
          - "runtime" (requires workspace)
        """
        if not cls._initialized:
            cls.initialize()

        if component not in {"system", "runtime"}:
            raise ValueError("component must be 'system' or 'runtime'")

        if component == "runtime" and not workspace:
            raise ValueError("workspace is required when component='runtime'")

        key = f"{component}:{workspace or 'global'}"
        if key in cls._loggers:
            return cls._loggers[key]

        logger = logging.getLogger(key)
        logger.setLevel(cls._level)
        logger.propagate = False

        log_path = cls._resolve_log_path(component, workspace)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | "
            "%(module)s:%(lineno)d | %(funcName)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        cls._loggers[key] = logger
        return logger

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_log_path(
        cls,
        component: str,
        workspace: Optional[str],
    ) -> Path:
        assert cls._base_dir is not None

        if component == "system":
            return cls._base_dir / "system.log"

        # component == "runtime"
        return cls._base_dir / "runtime" / f"{workspace}.log"

    @staticmethod
    def _parse_log_level(level: str) -> int:
        return {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }.get(level.upper(), logging.INFO)
