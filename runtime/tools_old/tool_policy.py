from __future__ import annotations
from typing import Dict, List
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

class ToolPolicy:
    """
    Workspace-level tool authorization.
    """

    def __init__(self, policy: Dict):
        self.policy = policy
        logger.info("Initializing Tool Policy")

    def allowed_tools_for_agent(self, agent_role: str) -> List[str]:
        tools = self.policy.get("agents", {}).get(agent_role, {}).get("tools", [])
        logger.debug(f"Allowed tools for {agent_role}: {tools}")
        return tools

    def check(self, agent_role: str, tool_name: str) -> bool:
        try:
            allowed = self.allowed_tools_for_agent(agent_role)
            if tool_name not in allowed:
                raise PermissionError(
                    f"Agent '{agent_role}' is not allowed to use tool '{tool_name}'"
                )
        except PermissionError as e:      
            logger.error(f"Caught a PermissionError: {e}")
            return False
        logger.info("Still continue 2")
        return True

