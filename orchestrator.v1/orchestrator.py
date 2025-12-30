from typing import Any, Dict, Optional
from graph.graph import build_graph
from events.event_bus import EventBus
from events.state_router import register_state_router
from runtime.session_control import SessionControl

class Orchestrator:
    def __init__(
            self,
            event_bus: Optional[EventBus] = None,
            agent_registry = None,
            stage_registry = None,
            graph_builder=None,
        ):
        self.event_bus = event_bus
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        register_state_router(self.event_bus)

        # Use custom graph builder (with HITL)
        if graph_builder:
            self.graph = graph_builder(agent_registry, stage_registry)
        else:
            self.graph = build_graph(agent_registry, stage_registry)

        self._wire_event_bus()

    def _wire_event_bus(self):
        for agent in self.agent_registry.all():
            agent.event_bus = self.event_bus
        for stage in self.stage_registry._stages.values():
            stage.set_event_bus(self.event_bus)

    async def run(self, session_id: str, task: str) -> Dict[str, Any]:

        # Initial State 
        state: Dict[str, Any] = {
            "session_id": session_id,  
            "task": task,
            "stage": self.stage_registry._order[0],
            "history": [],
            "history_agents": [],
            "executed_agents_per_stage": {},
            "winner": None,
            "rewards": {},
            "done": False,
        }

        await self.event_bus.emit(
                "orchestrator_start",
                {
                    "task": task,
                    "session_id": session_id,  # Useful for logging & memory
                    "initial_state": state,
                },
            )

        async for event in self.graph.astream(state):

            await self.event_bus.emit("graph_event", event)

            print("We are inside graph.astream - an event is emitted:")
            print(event)

            pass

    def _record_agent_execution(self, state: Dict, agent_role: str): 
        stage = state["stage"]
        per_stage = state.setdefault("executed_agents_per_stage", {})

        print("Now in record_agent_execution")
        print(f"stage: {stage}")

        print("Now in record_agent_execution")
        print(f"per_stage: {per_stage}")

        executed = per_stage.setdefault(stage, [])

        print("Now in record_agent_execution")
        print(f"Executed: {executed}")

        if agent_role not in executed:
            executed.append(agent_role)

        print("Now in record_agent_execution. Appending new executed agent")
        print(f"Executed: {executed}")

        # Also track globally
        history_agents = state.setdefault("history_agents", [])
        if agent_role not in history_agents:
            history_agents.append(agent_role)