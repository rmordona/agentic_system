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
from langgraph.graph import StateGraph
from graph.state import State, AgentOutput, set_default_channel
from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
from runtime.graph_manager import GraphManager
from runtime.logger import AgentLogger

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
        agent_registry: AgentRegistry,
        stage_registry: StageRegistry,
        graph_manager: GraphManager,  
        event_bus: EventBus,
        session_id: None,
        hitl_callback: Optional[Any] = None
    ):

        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        self.hitl_callback = hitl_callback
        self.event_bus = event_bus

        # Get the graph once per orchestrator
        self.graph = graph_manager.get(self.workspace_name)
        self.session_state: Dict[str, Any] = {}

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger( component="runtime", workspace = self.workspace_name )

    async def run(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the session through the LangGraph.
        Returns final session state.
        """
        print(f"session_sate: {session_state}")

        print("Just entered Orchestrator ...")
        logger.info("Just entered Orchestrator ...")

        await self.event_bus.emit(
                "orchestrator_start",
                {
                    "task": session_state["task"],
                    "session_id": session_state["session_id"],  # Useful for logging & memory
                    "initial_state": session_state,
                },
            )

        async for event in self.graph.astream(session_state):

            logger.info("We are inside graph.astream - an event is emitted ...")
            logger.info(event)

            logger.info("Emitting graph_event ...")

            await self.event_bus.emit("graph_event", event)
            logger.info("Now waiting for graph_event response")

        logger.info("Exited from graph.astream")

        await self.event_bus.emit(
                "orchestrator_end",
                {
                    "task": session_state["task"],
                    "session_id": session_state["session_id"],  # Useful for logging & memory
                    "initial_state": session_state,
                },
            )


        # Loop until graph signals done
        #while not self.session_state.get("done", False):
        #    # LangGraph runs asynchronously and returns deltas per node
        #    state_delta = self.graph.astream(self.session_state)

            # Merge deltas into session_state
            # self._merge_state_delta(state_delta)

        return self.session_state

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


