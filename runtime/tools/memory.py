from runtime.tools.base import Tool
from runtime.bootstrap.platform import Platform


class MemoryWriteTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def call(self, schema: str, payload: dict):
        await Platform.model_manager.memory_manager.store(**payload)
        return {"status": "ok"}


class MemoryReadTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def call(self, query: str, filters: dict | None = None):
        return {"memories": []}

