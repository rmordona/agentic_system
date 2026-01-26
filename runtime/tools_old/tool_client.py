from __future__ import annotations
from typing import Dict, Any
from runtime.tools.base import Tool
from runtime.tools.tool_registry import ToolRegistry
from runtime.tools.tool_policy import ToolPolicy
from runtime.logger import AgentLogger

#logger = AgentLogger.get_logger(component="system")

class ToolClient(Tool):
    """
    Execution gateway for tools.
    Used by agents.
    """
    def __init__(
        self,
        registry: ToolRegistry,
        policy: ToolPolicy,
        agent_role: str
    ):
        self.registry = registry
        self.policy = policy
        self.agent_role = agent_role

        self.logger = AgentLogger.get_logger(component="module", module=__name__)

    async def call(self, 
            tool_name: str, 
            **kwargs
            ) -> Dict[str, Any]:
        allowed = self.policy.check(self.agent_role, tool_name)
        if allowed:
            tool = self.registry.get(tool_name)
            self.logger.info(f"Running tool '{tool_name}' for '{self.agent_role}'")
            return await tool.call(**kwargs)
        self.logger.warning(f"'{self.agent_role}' is not allwed to run the tool '{tool_name}' ... Permission denied ...")
        return {}

