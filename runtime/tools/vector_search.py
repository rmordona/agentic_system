from runtime.tools.base import Tool
from runtime.bootstrap.platform import Platform


class VectorSearchTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def call(self, query: str, top_k: int = 5):
        return await Platform.model_manager.generate(
            query=query,
            top_k=top_k,
        )

