# runtime/logger.py

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Optional


BOOTSTRAP = {"memory_manager", "embedding_store", "tool_client"}

class AgentLogger:
    """
    Centralized logging factory.
    - Singleton
    - Workspace-aware
    - Component-scoped
    - Supports bootstrap and hub folders
    """

    _initialized = False
    _base_log_dir: Path
    _loggers: Dict[str, logging.Logger] = {}
    level: int = logging.INFO

    @staticmethod
    def _parse_log_level(level_str: str) -> int:
        """
        Convert string log level (INFO, DEBUG, WARNING, etc.) to logging module constant.
        """
        level_map = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,   # allow alias
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }
        return level_map.get(level_str.upper(), logging.INFO)

    @classmethod
    def initialize(
        cls,
        log_dir: Path,
        log_level: str
    ):
        """
        Initialize logging system once.
        """
        if cls._initialized:
            return

        cls._base_log_dir = log_dir
        cls._base_log_dir.mkdir(parents=True, exist_ok=True)

        cls.level = cls._parse_log_level(log_level)

        logging.basicConfig(level=cls.level)
        cls._initialized = True

    @classmethod
    def set_level(cls, level: int):
        for logger in cls._loggers.values():
            logger.setLevel(level)

    @classmethod
    def get_logger(
        cls,
        workspace: Optional[str],
        component: str,
    ) -> logging.Logger:
        """
        Returns a logger scoped to:
        - workspace=None & component in bootstrap → logs/bootstrap/<component>.log
        - workspace=None & component=hub → logs/hub/<component>.log
        - workspace=<workspace> → logs/workspaces/<workspace>/<component>.log
        """
        if not cls._initialized:
            raise RuntimeError("AgentLogger.initialize() must be called first")

        key = f"{workspace or 'hub'}::{component}"
        if key in cls._loggers:
            return cls._loggers[key]

        logger = logging.getLogger(key)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        # -------- Determine log path --------
        if workspace:
            log_path = cls._base_log_dir / "workspaces" / workspace / f"{component}.log"
        else:
            # Bootstrap components
            if component in BOOTSTRAP:
                log_path = cls._base_log_dir / "bootstrap" / f"{component}.log"
            else:
                # Hub-level components (WorkspaceHub, Orchestrator, etc.)
                log_path = cls._base_log_dir / "hub" / f"{component}.log"

        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        cls._loggers[key] = logger
        return logger
