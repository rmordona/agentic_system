from runtime.tools.base import Tool


class WebSearchTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]
        self.description = spec["description"]

    async def call(self, query: str):
        # Stub — replace with SerpAPI / Tavily / Bing
        return {"results": [f"Result for '{query}'"]}

