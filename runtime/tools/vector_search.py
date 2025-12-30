from runtime.tools.base import Tool
from runtime.platform_runtime import PlatformRuntime


class VectorSearchTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def run(self, query: str, top_k: int = 5):
        return await PlatformRuntime.embedding_store.query_embeddings(
            query=query,
            top_k=top_k,
        )

