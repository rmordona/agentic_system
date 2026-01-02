# llm/chat_model_factory.py

import json
from pathlib import Path
#from llm.core.registry import Registry
from llm.factory_registry import Registry

class ChatModelFactory:
    _registry = Registry()
    _config = None

    @classmethod
    def load_config(cls, path: str):
        cls._config = json.loads(Path(path).read_text())

    @classmethod
    def register(cls, name: str, chatmodel_cls):
        cls._registry.register(name, chatmodel_cls)

    @classmethod
    def get(cls, provider: str, model_name: str, **kwargs):
        if cls._config is None:
            raise RuntimeError("ChatModelFactory config not loaded")

        cfg = cls._config.get(provider)
        if not cfg:
            raise ValueError(f"No chatmodel config for '{provider}'")

        ChatCls = cls._registry.get(provider)
        endpoint = cfg["endpoint"]["base"]

        return ChatCls(
            model_name=model_name,
            endpoint=endpoint,
            **kwargs
        )
