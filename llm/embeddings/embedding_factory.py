# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/embeddings/embedding_factory.py
#
# Description:
#   EmbeddingFactory provides a production-ready, singleton factory for
#   dynamically instantiating embedding clients (Ollama, OpenAI, Cohere, etc.)
#   based on configuration files. Supports dynamic registration and lazy loading
#   of new embedding providers without modifying the factory code.
#
#   The factory resolves embedding implementations at runtime using provider
#   configuration, enabling seamless extensibility and pluggable embeddings
#   across the platform.
#
# Usage:
#   1. Load configuration:
#        EmbeddingFactory.load_config(path_to_json)
#
#   2. (Optional) Register custom embedding providers dynamically:
#        EmbeddingFactory.register("my_embedding", MyEmbeddingClient)
#
#   3. Instantiate embedding clients:
#        embedding = EmbeddingFactory.get(provider="ollama")
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

from llm.embeddings.base_client import BaseEmbeddingClient

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class EmbeddingFactory:
    """
    Singleton factory for dynamically loading embedding providers.
    """

    _config: dict | None = None
    _loaded: bool = False

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @classmethod
    def load_config(cls, path: Path | str) -> None:
        """
        Load embedding configuration once.
        """
        if cls._loaded:
            return

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Embedding config not found: {path}")

        cls._config = json.loads(path.read_text())
        cls._loaded = True

        logger.info("EmbeddingFactory config loaded")

    # ------------------------------------------------------------------
    # Internal: Dynamic Import
    # ------------------------------------------------------------------
    @classmethod
    def _load_class(cls, module_path: str, class_name: str) -> Type[BaseEmbeddingClient]:
        """
        Dynamically import module and return class reference.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Failed to import embedding module '{module_path}': {e}")

        try:
            return getattr(module, class_name)
        except AttributeError:
            raise ImportError(
                f"Embedding class '{class_name}' not found in module '{module_path}'"
            )

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    @classmethod
    def get(cls, provider: str = "default") -> BaseEmbeddingClient:
        """
        Instantiate an embedding client by provider name.
        """
        if cls._config is None:
            raise RuntimeError("EmbeddingFactory config not loaded")

        embedding_cfg = cls._config.get("embedding", {})
        cfg = embedding_cfg.get(provider)

        if not cfg:
            raise ValueError(f"No embedding config for provider '{provider}'")

        EmbeddingCls = cls._load_class(
            module_path=cfg["module"],
            class_name=cfg["class"]
        )

        # Remove factory-only keys
        kwargs = {k: v for k, v in cfg.items() if k not in {"module", "class"}}

        logger.debug(f"Instantiating embedding provider '{provider}'")

        return EmbeddingCls(**kwargs)
