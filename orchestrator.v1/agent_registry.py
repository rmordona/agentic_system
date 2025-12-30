"""
agent_registry.py

Manages registration and lookup of agents in the agentic LLM system.

Responsibilities:
- Dynamically register agents
- Enforce unique roles
- Provide lookup utilities for graph construction

Non-responsibilities:
- Executing agents
- Scheduling
- State management
"""

from typing import Dict, List, Any


class AgentRegistry:
    """
    Registry for dynamically registered agents.
    """

    def __init__(self):
        self._agents: Dict[str, Any] = {}

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------

    def register(self, agent: Any) -> None:
        """
        Register an agent instance.

        Args:
            agent: An instance with a unique `role` attribute.

        Raises:
            ValueError if role already exists or missing.
        """
        if not hasattr(agent, "role"):
            raise ValueError("Agent must have a 'role' attribute.")

        if agent.role in self._agents:
            raise ValueError(
                f"Agent with role '{agent.role}' is already registered."
            )

        self._agents[agent.role] = agent

    # -----------------------------------------------------------------
    # Accessors
    # -----------------------------------------------------------------

    def get(self, role: str) -> Any:
        """Retrieve an agent by role."""
        return self._agents.get(role)

    def all(self) -> List[Any]:
        """Return all registered agents."""
        return list(self._agents.values())

    def roles(self) -> List[str]:
        """Return all registered agent roles."""
        return list(self._agents.keys())

    # -----------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"AgentRegistry(roles={self.roles()})"
