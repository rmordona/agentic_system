from typing import Dict, Any, List, Type, Optional
from pydantic import BaseModel

from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_adapters.redis_adapter import RedisEpisodicAdapter
from runtime.memory_adapters.langmem_adapter import LangMemSemanticAdapter
from runtime.memory_schemas import (
    ProposalMemory,
    CritiqueMemory,
    SynthesizerMemory,
    SemanticMemory,
    EpisodicMemory,
)

from runtime.embeddings.base import EmbeddingStore
from runtime.logger import AgentLogger

SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "ProposalMemory": ProposalMemory,
    "CritiqueMemory": CritiqueMemory,
    "SynthesizerMemory": SynthesizerMemory,
    "SemanticMemory": SemanticMemory,
    "EpisodicMemory": EpisodicMemory,
}


class MemoryFactory:
    """
    Factory for creating MemoryAdapter instances based on configuration.
    Supports Redis (episodic/persistent) and LangMem (semantic) adapters.
    """

    logger = None

    def __init__():
        # Bind workspace logger ONCE
        if MemoryFactory.logger is None:
            MemoryFactory.logger = AgentLogger.get_logger(None, component="memory_factory")

        logger = MemoryFactory.logger


    @staticmethod
    def build(
        config: Dict[str, Any],
        *,
        llm=None,
        embedding_store: Optional[EmbeddingStore] = None,
    ) -> Optional[MemoryAdapter]:
        """
        Build a memory adapter instance from config.

        Args:
            config: Dict containing 'backend' and backend-specific parameters.
            llm: LLM chat model required for LangMem.
            embedding_store: EmbeddingStore required for LangMem semantic memory.

        Returns:
            MemoryAdapter instance or None if backend is not configured.
        """
        backend = config.get("backend")

        if backend is None:
            MemoryFactory.logger.info("No memory backend configured")
            return None

        # ----------------------------
        # Redis (episodic / persistent)
        # ----------------------------
        if backend.lower() == "redis":
            redis_cfg = config.get("redis", {})
            return RedisEpisodicAdapter(config=redis_cfg)

        # ----------------------------
        # LangMem (semantic)
        # ----------------------------
        if backend.lower() == "langmem":
            if not llm:
                raise ValueError("LangMem requires an LLM chat model")
            if not embedding_store:
                raise ValueError("LangMem requires an EmbeddingStore")

            schema_names = config.get("schemas", [])
            schemas: List[Type[BaseModel]] = []

            for name in schema_names:
                if name not in SCHEMA_REGISTRY:
                    raise ValueError(f"Unknown memory schema: {name}")
                schemas.append(SCHEMA_REGISTRY[name])

            return LangMemSemanticAdapter(
                chat_model=llm,
                schemas=schemas,
            )

        raise ValueError(f"Unsupported memory backend: {backend}")
