from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import chromadb
from llm.memory_adapters.base import MemoryAdapter
from llm.memory_schemas import EpisodicMemory, SemanticMemory

class ChromaDBAdapter(MemoryAdapter):
    def __init__(self, collection_name: str, chroma_client=None):
        self.collection_name = collection_name
        self.client = chroma_client or chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)


    def _key(self, key_namespace:tuple):
        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["agent"]
        namespace  = keys["namespace"]
        return f"{session_id}:{agent}:{stage}:{namespace}"

    async def store_memory(
        self,
        memory: Union[Dict, BaseModel, EpisodicMemory]
        #namespace: Optional[str] = None
    ) -> str:
        memory_dict = memory.model_dump()
        chrome_key = self._key(memory.key_namespace)

        # ChromaDB expects embeddings, so you’d embed the memory text if needed
        self.collection.add([chrome_key], [memory_dict])
        return chrome_key

    async def fetch_memory(
        self,
        key_namespace: tuple = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        # query logic based on metadata filters

        keys=dict(key_namespace)
        session_id = keys["session_id"]
        agent      = keys["agent"]
        stage      = keys["stage"]
        namespace  = keys["namespace"]

        results = self.collection.query(
            filter={"session_id": session_id} if session_id else {},
            n_results=limit
        )
        return results

    
    async def add_embeddings(
        self,
        memory: Union[Dict, BaseModel, SemanticMemory]
    ) -> None:
        """Add embeddings to the semantic store."""
        return

    async def semantic_search(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}

    async def query(
        self,
        query: str, 
        top_k: Optional[int] = None, 
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        return {}
