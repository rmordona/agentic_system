from __future__ import annotations
from typing import Dict, Any

from runtime.tools.registry import ToolRegistry
from runtime.tools.policy import ToolPolicy
from runtime.logger import AgentLogger


class ToolClient:
    """
    Execution gateway for tools.
    Used by agents.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        policy: ToolPolicy,
        agent_role: str,
    ):
        self.registry = registry
        self.policy = policy
        self.agent_role = agent_role
        self.logger = AgentLogger.get_logger(None, f"tool_client.{agent_role}")

    async def run(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        self.policy.check(self.agent_role, tool_name)
        tool = self.registry.get(tool_name)
        self.logger.info(f"Running tool '{tool_name}'")
        return await tool.run(**kwargs)

