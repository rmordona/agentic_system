# mcp_client.py
import httpx
from typing import Dict, Any

class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    async def call(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/tool/{tool_name}", json={"payload": payload})
            resp.raise_for_status()
            return resp.json()

