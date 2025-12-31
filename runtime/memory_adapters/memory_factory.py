# memory_factory.py

from typing import Dict, Any, List, Type, Optional
from pydantic import BaseModel

from runtime.logger import AgentLogger
from runtime.embeddings.base import EmbeddingStore

from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_adapters.redis_adapter import RedisEpisodicAdapter
from runtime.memory_adapters.langmem_adapter import LangMemSemanticAdapter
from runtime.memory_adapters.local_memory_adapter_bm25 import LocalMemoryAdapter
from runtime.memory_adapters.postgres_adapter import PostgresAdapter
from runtime.memory_adapters.oracle_adapter import OracleAdapter

from runtime.memory_schemas import (
    ProposalMemory,
    CritiqueMemory,
    SynthesizerMemory,
    SemanticMemory,
    EpisodicMemory,
)

# ---------------------------------------------------------------------------
# Schema Registry
# ---------------------------------------------------------------------------

SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "ProposalMemory": ProposalMemory,
    "CritiqueMemory": CritiqueMemory,
    "SynthesizerMemory": SynthesizerMemory,
    "SemanticMemory": SemanticMemory,
    "EpisodicMemory": EpisodicMemory,
}


# ---------------------------------------------------------------------------
# MemoryFactory
# ---------------------------------------------------------------------------

class MemoryFactory:
    """
    Factory responsible for constructing episodic and semantic memory adapters.

    Episodic adapters:
      - Persistent / CRUD-based memory
      - Intended for create_manage_memory_tool

    Semantic adapters:
      - Embedding-based semantic recall
      - Intended for create_search_memory_tool
    """

    def __init__(self):
        self.logger = AgentLogger.get_logger(
            None, component="memory_factory"
        )

    # ---------------------------------------------------------------------
    # Episodic Memory (CRUD / Persistent)
    # ---------------------------------------------------------------------

    @staticmethod
    def get_episodic_adapter(
        config: Dict[str, Any],
        *,
        workspace_name: Optional[str] = None,
        persist_path: Optional[str] = None,
    ) -> Optional[MemoryAdapter]:
        """
        Build an episodic (persistent / CRUD) memory adapter.

        Intended to be wrapped by create_manage_memory_tool.
        """
        if not config:
            return None

        backend = config.get("backend")
        if not backend:
            return None

        backend = backend.lower()

        # ----------------------------
        # Redis
        # ----------------------------
        if backend == "redis":
            return RedisEpisodicAdapter(
                config=config.get("redis", {})
            )

        # ----------------------------
        # Local in-memory
        # ----------------------------
        if backend == "local-in-memory":
            if not workspace_name:
                raise ValueError(
                    "LocalMemoryAdapter requires workspace_name"
                )

            return LocalMemoryAdapter(
                workspace_name=workspace_name,
                persist_path=persist_path,
            )

        # ----------------------------
        # Postgres
        # ----------------------------
        if backend == "postgres":
            dsn = config.get("dsn")
            table_name = config.get(
                "table_name", "episodic_memories"
            )

            if not dsn:
                raise ValueError(
                    "Postgres episodic backend requires a DSN"
                )

            return PostgresAdapter(
                dsn=dsn,
                table_name=table_name,
            )

        # ----------------------------
        # Oracle
        # ----------------------------
        if backend == "oracle":
            dsn = config.get("dsn")
            table_name = config.get(
                "table_name", "episodic_memories"
            )

            if not dsn:
                raise ValueError(
                    "Oracle episodic backend requires a DSN"
                )

            return OracleAdapter(
                dsn=dsn,
                table_name=table_name,
            )

        return None

    # ---------------------------------------------------------------------
    # Semantic Memory (Embeddings / Retrieval)
    # ---------------------------------------------------------------------

    @staticmethod
    def get_semantic_adapter(
        config: Dict[str, Any],
        *,
        llm=None,
        embedding_store: Optional[EmbeddingStore] = None,
    ) -> Optional[MemoryAdapter]:
        """
        Build a semantic (embedding-based) memory adapter.

        Intended to be wrapped by create_search_memory_tool.
        """
        if not config:
            return None

        backend = config.get("backend")
        if not backend:
            return None

        backend = backend.lower()

        # ----------------------------
        # LangMem
        # ----------------------------
        if backend == "langmem":
            if not llm:
                raise ValueError(
                    "LangMem semantic memory requires an LLM"
                )
            if not embedding_store:
                raise ValueError(
                    "LangMem semantic memory requires an EmbeddingStore"
                )

            schema_names = config.get("schemas", [])
            schemas: List[Type[BaseModel]] = []

            for name in schema_names:
                if name not in SCHEMA_REGISTRY:
                    raise ValueError(
                        f"Unknown memory schema: {name}"
                    )
                schemas.append(SCHEMA_REGISTRY[name])

            return LangMemSemanticAdapter(
                chat_model=llm,
                schemas=schemas,
            )

        # ----------------------------
        # Postgres
        # ----------------------------
        if backend == "postgres":
            dsn = config.get("dsn")
            table_name = config.get(
                "table_name", "semantic_memories"
            )

            if not dsn:
                raise ValueError(
                    "Postgres semantic backend requires a DSN"
                )

            return PostgresAdapter(
                dsn=dsn,
                table_name=table_name,
            )

        # ----------------------------
        # Oracle
        # ----------------------------
        if backend == "oracle":
            dsn = config.get("dsn")
            table_name = config.get(
                "table_name", "semantic_memories"
            )

            if not dsn:
                raise ValueError(
                    "Oracle semantic backend requires a DSN"
                )

            return OracleAdapter(
                dsn=dsn,
                table_name=table_name,
            )

        return None

