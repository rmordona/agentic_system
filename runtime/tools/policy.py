from __future__ import annotations
from typing import Dict, List
from runtime.logger import AgentLogger


class ToolPolicy:
    """
    Workspace-level tool authorization.
    """

    def __init__(self, policy: Dict):
        self.logger = AgentLogger.get_logger(None, "tool_policy")
        self.policy = policy

    def allowed_tools_for_agent(self, agent_role: str) -> List[str]:
        tools = self.policy.get("agents", {}).get(agent_role, {}).get("tools", [])
        self.logger.debug(f"Allowed tools for {agent_role}: {tools}")
        return tools

    def check(self, agent_role: str, tool_name: str):
        allowed = self.allowed_tools_for_agent(agent_role)
        if tool_name not in allowed:
            raise PermissionError(
                f"Agent '{agent_role}' is not allowed to use tool '{tool_name}'"
            )

