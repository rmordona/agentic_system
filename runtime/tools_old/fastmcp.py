from runtime.tools.base import Tool
from fastmcp import Client

class FastMCPClientTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]
        self.description = spec["description"]

    async def call(self, *, endpoint: str, service: str, params: dict, timeout: float = 30.0):
        async with Client(endpoint) as client:
            return await client.call(service=service, params=params,  timeout=timeout)

