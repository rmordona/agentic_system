# llm/stores/providers.py
"""
Store provider registry.

Importing this module ensures that all store implementations
are registered with StoreFactory via side-effect imports.
"""

from llm.stores.inmemory_store import InMemoryStore  # In-memory store (default / fallback)
from llm.stores.redis_store import RedisStore  # Redis
from llm.stores.chroma_store import ChromaStore  # ChromaDB
from llm.stores.postgres_store import PostgresStore  # PostgreSQL (pgvector)
from llm.stores.oracle_store import OracleStore  # Oracle (vector-native)

