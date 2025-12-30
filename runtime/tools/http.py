import aiohttp
from runtime.tools.base import Tool


class HttpRequestTool(Tool):
    def __init__(self, spec: dict):
        self.name = spec["name"]

    async def run(self, method: str, url: str, headers=None, body=None):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=body) as resp:
                return {
                    "status": resp.status,
                    "response": await resp.json()
                }

