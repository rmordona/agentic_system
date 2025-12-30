from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio

class Stage(ABC):
    """
    Base class for stages in the agentic AI system.

    Responsibilities:
    - Track allowed agents
    - Emit enter/exit events
    - Provide exit logic
    - Define routing policy
    """

    name: str
    allowed_agents: List[str]
    event_bus = None
    terminal: bool = False  # mark final stage

    def __init__(self, name: str, allowed_agents: List[str], terminal: bool = False):
        self.name = name
        self.allowed_agents = allowed_agents
        self.terminal = terminal

    # -----------------------------
    # Event handling
    # -----------------------------
    def set_event_bus(self, event_bus):
        self.event_bus = event_bus

    def on_enter(self, state: Dict[str, Any]):
        """
        Called when stage is entered.
        """
        state.setdefault("executed_agents_per_stage", {}).setdefault(self.name, [])
        if self.event_bus:
            asyncio.create_task(self.event_bus.emit("stage_enter", {"stage": self.name, "state": state}))

    def on_exit(self, state: Dict[str, Any]):
        """
        Called when stage is exited.
        """
        if self.event_bus:
            asyncio.create_task(self.event_bus.emit("stage_exit", {"stage": self.name, "state": state}))

    # -----------------------------
    # Stage lifecycle logic
    # -----------------------------
    @abstractmethod
    def routing_policy(self, state: Dict[str, Any], registry) -> List[str]:
        """
        Return list of agent roles that can execute next.
        Override per stage if needed.
        """
        # By default, all allowed agents in this stage
        return self.allowed_agents

    @abstractmethod
    def should_exit(self, state: Dict[str, Any]) -> bool:
        """
        Return True if the stage is done.

        IMPORTANT: Only consider agents allowed in this stage to avoid infinite loops.
        """
        executed = state.get("history_agents", [])
        return all(agent in executed for agent in self.allowed_agents)

    def __repr__(self):
        return f"Stage(name={self.name}, allowed_agents={self.allowed_agents}, terminal={self.terminal})"
