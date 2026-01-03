import chromadb
from langgraph.store.base import BaseStore

class ChromaStore(BaseStore):
    def __init__(
        self,
        persist_dir: str | None = None,
        collection: str = "agent_memory",
    ):
        self.client = chromadb.Client(
            chromadb.Settings(
                persist_directory=persist_dir
            ) if persist_dir else None
        )
        self.collection = self.client.get_or_create_collection(collection)

    async def put(self, key, value, *, namespace=None):
        self.collection.add(
            ids=[key],
            documents=[value["data"]],
            embeddings=[value["embedding"]],
            metadatas=[{"namespace": namespace}],
        )

    async def set(self, key, value):
        self.collection.upsert(
            ids=[key],
            documents=[str(value)]
        )

    async def get(self, key, *, namespace=None):
        res = self.collection.get(ids=[key])
        return res["documents"][0] if res["documents"] else None

    async def search(self, query_vector, *, namespace=None, top_k=5):
        res = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"namespace": namespace} if namespace else None,
        )
        return res["documents"][0]

