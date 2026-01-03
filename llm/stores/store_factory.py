# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/stores/store_factory.py
#
# Description:
#   StoreFactory provides a production-ready, singleton factory for
#   dynamically instantiating memory store backends (In-Memory, Redis,
#   Chroma, Postgres, Oracle, etc.) based on configuration files.
#
#   The factory supports dynamic provider registration and lazy loading,
#   allowing new storage backends to be integrated without modifying
#   factory logic. This enables flexible memory persistence strategies
#   across semantic and episodic memory layers.
#
# Usage:
#   1. Load configuration:
#        StoreFactory.load_config(path_to_json)
#
#   2. (Optional) Register custom store providers dynamically:
#        StoreFactory.register("my_store", MyStoreBackend)
#
#   3. Instantiate stores:
#        store = StoreFactory.get(provider="in-memory")
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-02
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import importlib
from pathlib import Path
from typing import Type

from langgraph.store.base import BaseStore

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class StoreFactory:
    """
    Singleton factory for dynamically loading memory stores.
    """

    _config: dict | None = None
    _loaded: bool = False

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @classmethod
    def load_config(cls, path: Path | str) -> None:
        """
        Load store configuration once.
        """
        if cls._loaded:
            return

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Store config not found: {path}")

        cls._config = json.loads(path.read_text())
        cls._loaded = True

        logger.info("StoreFactory config loaded")

    # ------------------------------------------------------------------
    # Internal: Dynamic Import
    # ------------------------------------------------------------------
    @classmethod
    def _load_class(cls, module_path: str, class_name: str) -> Type[BaseStore]:
        """
        Dynamically import module and return class reference.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Failed to import store module '{module_path}': {e}")

        try:
            return getattr(module, class_name)
        except AttributeError:
            raise ImportError(
                f"Store class '{class_name}' not found in module '{module_path}'"
            )

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    @classmethod
    def get(cls, provider: str = "default") -> BaseStore:
        """
        Instantiate a memory store backend by provider name.
        """
        if cls._config is None:
            raise RuntimeError("StoreFactory config not loaded")

        stores_cfg = cls._config.get("stores", {})
        cfg = stores_cfg.get(provider)

        if not cfg:
            raise ValueError(f"No store config for provider '{provider}'")

        StoreCls = cls._load_class(
            module_path=cfg["module"],
            class_name=cfg["class"]
        )

        kwargs = {k: v for k, v in cfg.items() if k not in {"module", "class"}}

        logger.debug(f"Instantiating store provider '{provider}'")

        return StoreCls(**kwargs)
