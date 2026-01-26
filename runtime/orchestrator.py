# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/orchestrator.py
#
# Description:
#
#   Orchestrator manages a single session’s execution through a LangGraph.
#
#    It owns session state, drives graph execution, emits lifecycle events,
#    and integrates optional human-in-the-loop callbacks.
#
#    Orchestrator does NOT execute agent logic or manage memory directly.
#    It coordinates, it does not compute.
#   
#
# Author: Raymond M.O. Ordona
# Created: 2025-12-31
# Copyright:
#   © 2025 Raymondn Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional
from events.event_bus import EventBus
#from langgraph.graph import StateGraph

#from runtime.agent_registry import AgentRegistry
#from runtime.stage_registry import StageRegistry
#from runtime.stage_manager import StageManager
#from runtime.runtime_context import RuntimeContext

#from runtime.graph.stage_state import StateSchema, AgentOutput, set_default_channel

from runtime.core_engine import CoreEngine

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger( component="system" )

class Orchestrator:
    """
    Per-session orchestrator that manages execution of a LangGraph graph
    for a given session and workspace.

    Responsibilities:
    - Maintain session state
    - Route stages via stage_router node in the graph
    - Fetch and persist memory for SkillAgents
    - Emit events to the EventBus
    - Handle optional HITL callbacks
    """

    def __init__(
        self,
        workspace_path: Path, 
        session_id: None, 
        event_bus: EventBus,

        hitl_callback: Optional[Any] = None
    ):

        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.session_id = session_id
        self.event_bus = event_bus
        self.hitl_callback = hitl_callback


        # Get the graph once per orchestrator
        #self.stage_graph = stage_manager.get(self.workspace_name)
        self.session_state: Dict[str, Any] = {}

        # Bind workspace logger ONCE
        #global logger
        #logger = AgentLogger.get_logger( component="runtime", workspace = self.workspace_name)


    async def run(self, user_intent: str, workspace_meta: dict) -> Dict[str, Any]:
        """
        Run the session through the LangGraph.
        Returns final session state.
        """

        logger.info("Just entered the Orchestrator... Now instantiating the Core Engine ...")
        self.core_engine = CoreEngine(self.session_id, user_intent, workspace_meta, self.workspace_path)

        # Compile the graph.
        logger.info("Compile the Graph ...")
        self._graph = self.core_engine.compile()

        # Get the initial State
        self.initial_state = await self.core_engine.initialize_state(user_intent)
        self.initial_state.model_rebuild()

        logger.info(f"Start with an initial state: {self.initial_state}")

        await self.event_bus.emit(
                "orchestrator_start",
                {
                    "task": self.initial_state.task,
                    "session_id": self.initial_state.session_id,  # Useful for logging & memory
                    "initial_state": self.initial_state,
                },
            )

        # steam_mode = <updates|values>
        # Configuration: The 'thread_id' allows for state persistence
        config = {
            "configurable": {"thread_id": "session_123"},
            "recursion_limit": 50  # Safety valve: Max 50 node transitions
        }

        async for event in self._graph.astream(self.initial_state, config, stream_mode="updates"):

            logger.info("<-------------------- We are inside graph.astream - an event is emitted ... -------------------> ")
            logger.info(f"Event yield: {event}")

            logger.info("Emitting graph_event ...")

            await self.event_bus.emit("graph_event", event)
            logger.info("Now waiting for graph_event response")

        logger.info("Exited from graph.astream")

        await self.event_bus.emit(
                "orchestrator_end",
                {
                    "task": self.initial_state.task,
                    "session_id": self.initial_state.session_id,  # Useful for logging & memory
                    "initial_state": self.initial_state,
                },
            )

        return self.initial_state

    def _merge_state_delta(self, delta: Dict[str, Any]):
        """
        Merge LangGraph node delta into session state.
        Handles history, rewards, winner, decision, executed_agents_per_stage.
        """
        for key, value in delta.items():
            if key == "history_agents":
                self.session_state.setdefault("history_agents", []).extend(value)
            elif key == "rewards":
                for k, v in value.items():
                    self.session_state.setdefault("rewards", {}).setdefault(k, 0.0)
                    self.session_state["rewards"][k] += v
            elif key in {"winner", "decision"}:
                self.session_state[key] = value
            elif key == "executed_agents_per_stage":
                for stage, agents in value.items():
                    self.session_state.setdefault("executed_agents_per_stage", {}).setdefault(stage, [])
                    for agent in agents:
                        if agent not in self.session_state["executed_agents_per_stage"][stage]:
                            self.session_state["executed_agents_per_stage"][stage].append(agent)
            else:
                self.session_state[key] = value

    async def run_agent(self, agent_role: str) -> Any:
        """
        Run a single agent node in the graph.
        Useful for testing or for targeted HITL interventions.
        """
        agent = self.agent_registry.get(agent_role)
        if not agent:
            raise ValueError(f"Agent '{agent_role}' not found")

        output = await agent.run(self.session_state)
        delta = {
            "history_agents": [AgentOutput(
                stage=self.session_state["stage"],
                role=agent_role,
                output=output
            )],
            "executed_agents_per_stage": {
                self.session_state["stage"]: [agent_role]
            }
        }

        self._merge_state_delta(delta)
        return output

    async def hitl_decision(self, decision: Any):
        """
        Invoke HITL callback if defined.
        Can be used to skip stages or force agent selection.
        """
        if self.hitl_callback:
            return await self.hitl_callback(self.session_state, decision)
        return None


