import logging
from typing import Dict, Any, Optional
from runtime.embeddings.base import EmbeddingStore
#from runtime.embeddings.chroma_store import ChromaEmbeddingStore
from runtime.embeddings.postgres_store import PostgresEmbeddingStore
from runtime.logger import AgentLogger

EMBEDDING_BACKENDS = {

    "postgres": PostgresEmbeddingStore,
    # "chromadb": ChromaEmbeddingStore,
    # "faiss": FaissEmbeddingStore,  
    # "pinecone": PineconeEmbeddingStore,
    # "oracle" : OracleEmbeddingStore
}

class EmbeddingFactory:
    """
    Factory to create EmbeddingStore instances based on config.
    """

    @staticmethod
    def build(config: Dict[str, Any], logger: logging.Logger) -> EmbeddingStore:
        """
        Build an embedding store based on config.
        Args:
            config: Dict with keys "backend" and backend-specific parameters
        Returns:
            EmbeddingStore instance
        """
        backend = config.get("backend")
        if not backend:
            raise ValueError("Embedding config must specify a 'backend' field")



        backend_class = EMBEDDING_BACKENDS.get(backend.lower())
        if not backend_class:
            raise ValueError(f"Unsupported embedding backend: {backend}")

        store_config = config[backend.lower()]

        instance = backend_class(config=store_config)
        logger.info(f"Initialized embedding store '{backend}' with params: {store_config}")
        return instance

