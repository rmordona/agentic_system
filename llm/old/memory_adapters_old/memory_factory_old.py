from typing import Dict, Any, List, Type, Optional
from pydantic import BaseModel

from runtime.memory_adapters.base import MemoryAdapter
from runtime.memory_adapters.redis_adapter import RedisEpisodicAdapter
from runtime.memory_adapters.langmem_adapter import LangMemSemanticAdapter
from runtime.memory_adapters.local_memory_adapter_bm25 import LocalMemoryAdapter
from runtime.memory_adapters.oracle_adapter import OracleAdapter 
from runtime.memory_adapters.postgres_adapter import PostgresAdapter 
#from runtime.memory_adapters.chromadb_adapter import ChromaDBAdapter 
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
    Supports Redis, LangMem, Local in-memory, and ChromaDB adapters.
    """

    def __init__(self):
        global logger
        logger = AgentLogger.get_logger(None, component="memory_factory")

    @staticmethod
    def build(
        config: Dict[str, Any],
        *,
        llm=None,
        embedding_store: Optional[EmbeddingStore] = None,
        workspace_name: Optional[str] = None,
        persist_path: Optional[str] = None,
        chroma_client=None,
    ) -> Optional[MemoryAdapter]:
        """
        Build a memory adapter instance from config.

        Args:
            config: Dict containing 'backend' and backend-specific parameters.
            llm: LLM chat model required for LangMem.
            embedding_store: EmbeddingStore required for LangMem semantic memory.
            workspace_name: optional workspace name for LocalMemoryAdapter.
            persist_path: optional path to store local memory JSON.
            chroma_client: optional ChromaDB client instance.

        Returns:
            MemoryAdapter instance or None if backend is not configured.
        """
        backend = config.get("backend")

        if backend is None:
            logger.info("No memory backend configured")
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

        # ----------------------------
        # Local in-memory adapter
        # ----------------------------
        if backend.lower() == "local-in-memory":
            if not workspace_name:
                raise ValueError("LocalMemoryAdapter requires workspace_name")
            return LocalMemoryAdapter(
                workspace_name=workspace_name,
                persist_path=persist_path,
            )

        # ----------------------------
        # ChromaDB adapter
        # ----------------------------
        ''' chromadb depends on onnxruntime 1.4.1 but does not have support for python3.14 (as of Dec 2025)
        if backend.lower() == "chromadb":
            collection_name = config.get("collection_name")
            if not collection_name:
                raise ValueError("ChromaDBAdapter requires a 'collection_name'")
            return ChromaDBAdapter(
                collection_name=collection_name,
                chroma_client=chroma_client,
            )
        '''
        #---------------------------
        # Postgres (episodic/semantic)
        # ----------------------------
        if backend_lower == "postgres":
            dsn = config.get("dsn")
            table_name = config.get("table_name", "memories")
            if not dsn:
                raise ValueError("Postgres backend requires a DSN")
            return PostgresMemoryAdapter(dsn=dsn, table_name=table_name)

        # ----------------------------
        # Oracle (episodic/semantic)
        # ----------------------------
        if backend_lower == "oracle":
            dsn = config.get("dsn")
            table_name = config.get("table_name", "memories")
            if not dsn:
                raise ValueError("Oracle backend requires a DSN")
            return OracleMemoryAdapter(dsn=dsn, table_name=table_name)

        raise ValueError(f"Unsupported memory backend: {backend}")
