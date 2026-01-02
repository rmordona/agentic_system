# runtime/embedding/chroma_store.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from llm.embeddings.base import EmbeddingStore
from runtime.logger import AgentLogger
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions

class ChromaEmbeddingStore(EmbeddingStore):
    """
    Concrete Chroma DB embedding store.
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "agentic_embeddings",
        embedding_dim: int = 1536,
    ):
        self.logger = AgentLogger.get_logger(workspace=None, component="chroma_store")
        self.client = Client(Settings(
            persist_directory=persist_directory,
            chroma_db_impl="duckdb+parquet",
        ))
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # Use OpenAI-compatible embedding function as default
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction(
            embedding_dimension=embedding_dim
        )

        # Get or create collection
        if self.collection_name in [c.name for c in self.client.list_collections()]:
            self.collection = self.client.get_collection(self.collection_name)
        else:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )

        self.logger.info(f"Initialized ChromaEmbeddingStore: {self.collection_name}")

    async def add_embeddings(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        self.collection.add(
            embeddings=vectors,
            metadatas=metadata,
        )
        self.logger.debug(f"Added {len(vectors)} embeddings to collection {self.collection_name}")

    async def query_embeddings(
        self, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filters or {},
        )
        self.logger.debug(f"Queried top {top_k} embeddings with filters={filters}")
        return result["metadatas"][0] if "metadatas" in result else []

    async def delete_embeddings(self, filters: Dict[str, Any]) -> None:
        self.collection.delete(where=filters)
        self.logger.debug(f"Deleted embeddings from {self.collection_name} with filters={filters}")

    async def clear(self) -> None:
        self.collection.delete(where={})
        self.logger.info(f"Cleared all embeddings in collection {self.collection_name}")

