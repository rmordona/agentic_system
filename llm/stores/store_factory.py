# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/store_factory.py
#
# Description:
#   StoreFactory dynamically instantiates store adapters based on a JSON configuration.
#   Supports: in-memory, Oracle, ChromaDB, Postgres, Redis
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------
import json
from pathlib import Path
from llm.factory_registry import Registry

class StoreFactory:
    _config = None
    _registry = Registry()

    @classmethod
    def load_config(cls, path: str):
        cls._config = json.loads(Path(path).read_text())

    @classmethod
    def get(cls, store_name: str = "default"):
        if cls._config is None:
            raise RuntimeError("StoreFactory config not loaded")

        store_cfg = cls._config.get(store_name)
        if store_cfg is None:
            raise ValueError(f"No config for store '{store_name}'")

        store_type = store_cfg.get("type", store_name.lower())
        StoreCls = cls._registry.get(store_type)
        return StoreCls(**store_cfg)

    @classmethod
    def register(cls, name: str, store_cls):
        cls._registry.register(name.lower(), store_cls)
