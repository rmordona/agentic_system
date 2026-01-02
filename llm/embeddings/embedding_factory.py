# llm/embeddings/embedding_factory.py

import json
from pathlib import Path
from llm.embeddings.base_client import BaseEmbeddingClient
from llm.factory_registry import Registry

class EmbeddingFactory:
    _config = None
    _registry = Registry()

    @classmethod
    def load_config(cls, path: str):
        cls._config = json.loads(Path(path).read_text())

    @classmethod
    def get(cls, provider: str = "default") -> BaseEmbeddingClient:
        if cls._config is None:
            raise RuntimeError("EmbeddingFactory config not loaded")
        provider_cfg = cls._config.get(provider)
        if provider_cfg is None:
            raise ValueError(f"No config for embedding provider '{provider}'")

        cls_name = provider_cfg.get("type", provider.lower())
        EmbeddingCls = cls._registry.get(cls_name)
        return EmbeddingCls(**provider_cfg)

    @classmethod
    def register(cls, name: str, embedding_cls):
        cls._registry.register(name.lower(), embedding_cls)
