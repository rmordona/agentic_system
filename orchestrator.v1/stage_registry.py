"""
stage_registry.py

Manages stages in the agentic LLM system.

Responsibilities:
- Define execution stages
- Preserve ordering
- Enforce allowed agents per stage
- Track executed agents per stage
- Provide lifecycle hooks (enter/exit)
- Provide next-stage lookup

Non-responsibilities:
- Executing agents
- Scheduling
- Parallelism (handled by LangGraph)
"""

from typing import Dict, List, Callable, Optional, Any
from events.event_bus import EventBus

class Stage:
    """
    Represents a single stage in the agentic system.
    """

    def __init__(
        self,
        name: str,
        allowed_agents: List[str],
        exit_condition: Callable[[Dict[str, Any]], bool],
        terminal: bool = False
    ):
        """
        Initialize a stage.

        Args:
            name: Unique stage name.
            allowed_agents: List of agent roles allowed in this stage.
            exit_condition: Callable returning True when stage should exit.
        """
        self.name = name
        self.allowed_agents = allowed_agents
        self.exit_condition = exit_condition
        self.terminal = terminal
        self.event_bus = None

    # -----------------------------------------------------------------
    # Lifecycle hooks
    # -----------------------------------------------------------------

    def set_event_bus(self, event_bus):
        """Inject an EventBus for observability."""
        self.event_bus = event_bus

    def on_enter(self, state: Dict[str, Any]) -> None:
        """Called when stage is entered."""
        # Initialize per-stage executed agents list
        state.setdefault("executed_agents_per_stage", {}).setdefault(self.name, [])

        if self.event_bus:
            self.event_bus.emit_sync(
                "stage_enter", {"stage": self.name, "state": state}
            )

    def on_exit(self, state: Dict[str, Any]) -> None:
        """Called when stage is exited."""
        if self.event_bus:
            self.event_bus.emit_sync(
                "stage_exit", {"stage": self.name, "state": state}
            )

    # -----------------------------------------------------------------
    # Exit logic
    # -----------------------------------------------------------------

    def should_exit(self, state: Dict[str, Any]) -> bool:
        """Return True if this stage should exit based on state."""
        # Pass state including executed agents to exit_condition
        print(f"Exit state: {state}")
        print(f"[Exit Condition]: {self.exit_condition(state)}")
        return bool(self.exit_condition(state))

    def __repr__(self) -> str:
        return f"Stage(name={self.name}, allowed_agents={self.allowed_agents})"


class StageRegistry:
    """
    Registry to store ordered stages.
    """

    def __init__(self):
        self._stages: Dict[str, Stage] = {}
        self._order: List[str] = []

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------

    def add_stage(
        self,
        stage: Stage
    ) -> None:
        """
        Add a new Stage instance to the registry.

        Args:
            stage: Stage instance to register

        Raises:
            ValueError if stage name already exists.
        """
        if stage.name in self._stages:
            raise ValueError(f"Stage '{stage.name}' already exists.")

        self._stages[stage.name] = stage
        self._order.append(stage.name)

    # -----------------------------------------------------------------
    # Accessors
    # -----------------------------------------------------------------

    def get(self, name: str) -> Stage:
        """Retrieve a stage by name."""
        return self._stages[name]

    def next_stage(self, current_name: str) -> Optional[str]:
        """Return the next stage name after current, or None if last."""
        try:
            index = self._order.index(current_name)
        except ValueError:
            raise ValueError(f"Unknown stage '{current_name}'.")

        if index + 1 < len(self._order):
            return self._order[index + 1]
        return None

    def all(self) -> List[Stage]:
        """Return all stages in order."""
        return [self._stages[name] for name in self._order]

    # -----------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        return f"StageRegistry(stages={self._order})"
