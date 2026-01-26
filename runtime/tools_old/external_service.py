from runtime.tools.base import Tool

class ExternalServiceTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]
        self.description = spec["description"]

    async def call(self, query: str, params: dict):
        # Example: call external API
        return await some_http_client.post(url="https://api.example.com", json=params)

