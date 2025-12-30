from __future__ import annotations
from typing import Any, Dict
from fastmcp import Client
from runtime.logger import AgentLogger

class ToolClient:
    """
    Wraps FastMCP for tool invocation.
    Supports:
    - Dynamic tools per agent
    - Async execution
    - Handles session and state context
    """

    logger = None

    def __init__(self, endpoint: str, api_key: str = None):
        # Bind workspace logger ONCE
        if ToolClient.logger is None:
            ToolClient.logger = AgentLogger.get_logger(None, component="tool_client")

        logger = ToolClient.logger

        self.client = Client(endpoint=endpoint, api_key=api_key)

    async def call(self, service: str, params: Dict[str, Any], timeout: float = 30.0) -> Any:
        """
        Call a remote tool/service via Client.
        """
        try:
            result = await self.client.call(service, params=params, timeout=timeout)
            logger.debug(f"Tool {service} called with params={params}")
            return result
        except Exception as e:
            logger.error(f"Error calling tool {service}: {e}")
            return None


