from runtime.tools.base import Tool
from runtime.platform_runtime import PlatformRuntime


class MemoryWriteTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def run(self, schema: str, payload: dict):
        await PlatformRuntime.memory_manager.store(**payload)
        return {"status": "ok"}


class MemoryReadTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def run(self, query: str, filters: dict | None = None):
        return {"memories": []}

