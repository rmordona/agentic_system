# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/chatmodels/chat_model_factory.py
#
# Description:
#   ChatModelFactory provides a production-ready, singleton factory for
#   dynamically instantiating chat model clients (Ollama, OpenAI, Cohere, etc.)
#   based on configuration files. Supports dynamic registration of new chat
#   model providers without modifying the factory code.
#
# Usage:
#   1. Load configuration: ChatModelFactory.load_config(path_to_json)
#   2. Register new chatmodel providers via ChatModelFactory.register(name, cls)
#   3. Instantiate models: ChatModelFactory.get(provider="ollama", model_name="qwen2.5")
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-02
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

# llm/chatmodels/chatmodel_factory.py

import json
import importlib
from pathlib import Path
from typing import Type

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class ChatModelFactory:
    """
    Dynamically loads and instantiates chat models based on configuration.
    No provider imports at module load time.
    """

    _config: dict | None = None
    _loaded: bool = False

    @classmethod
    def load_config(cls, path: Path) -> None:
        if cls._loaded:
            return

        cls._config = json.loads(path.read_text())
        cls._loaded = True
        logger.info("ChatModelFactory config loaded")

    @classmethod
    def _load_class(cls, module_path: str, class_name: str) -> Type:
        """
        Dynamically import module and return class reference.
        """
        module = importlib.import_module(module_path)
        try:
            return getattr(module, class_name)
        except AttributeError:
            raise ImportError(
                f"Class '{class_name}' not found in module '{module_path}'"
            )

    @classmethod
    def get(cls, provider: str, model_name: str, **kwargs):
        if cls._config is None:
            raise RuntimeError("ChatModelFactory config not loaded")

        cfg = cls._config.get(provider)
        if not cfg:
            raise ValueError(f"No chatmodel config for '{provider}'")

        ChatCls = cls._load_class(
            module_path=cfg["module"],
            class_name=cfg["class"]
        )

        endpoint = cfg.get("endpoint", {}).get("base")

        return ChatCls(
            model_name=model_name,
            endpoint=endpoint,
            **kwargs
        )
