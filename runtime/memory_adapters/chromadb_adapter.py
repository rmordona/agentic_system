from runtime.memory_adapters.base import MemoryAdapter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import chromadb

class ChromaDBAdapter(MemoryAdapter):
    def __init__(self, collection_name: str, chroma_client=None):
        self.collection_name = collection_name
        self.client = chroma_client or chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)

    async def store_memory(self, memory: BaseModel) -> str:
        memory_dict = memory.model_dump()
        key = memory_dict.get("session_id") + "-" + memory_dict.get("agent")
        # ChromaDB expects embeddings, so you’d embed the memory text if needed
        self.collection.add([key], [memory_dict])
        return key

    async def fetch_memory(
        self,
        session_id: Optional[str] = None,
        task: Optional[str] = None,
        agent: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        # query logic based on metadata filters
        results = self.collection.query(
            filter={"session_id": session_id} if session_id else {},
            n_results=limit
        )
        return results

