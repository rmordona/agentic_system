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
from core.paths import WORKSPACES_ROOT

import sys
import time
import json
import itertools
import asyncio

from uuid import UUID
from enum import Enum

from datetime import datetime
from typing import Any, Dict, Optional
from events.event_bus import EventBus

from langgraph.types import Command

from runtime.artifact_factory import Task
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
        workspace_name: str,
        core_engine: CoreEngine, 
        session_id: None, 
        event_bus: EventBus,
        hitl_callback: Optional[Any] = None
    ):

        self.workspace_path = WORKSPACES_ROOT /workspace_name
        self.workspace_name = workspace_name

        self.session_id = session_id
        self.event_bus = event_bus
        self.hitl_callback = hitl_callback

        self.session_state: Dict[str, Any] = {}

        self.core_engine = core_engine
        self._graph = self.core_engine.compiled_graph


    async def run_stream(self, user_intent: str, session_id: str):
        """
        Async generator for WebSocket streaming.
        """
        self.initial_state = await self.core_engine.acquire_new_state(user_intent, session_id)
        self.initial_state.model_rebuild()

        config = {
            "configurable": {"thread_id": session_id},  # Use session_id as LangGraph thread
            "recursion_limit": 8
        }

        print("GRAPH ID RUN:", id(self._graph))
        print("CHECKPOINTER ID RUN:", id(self._graph.checkpointer))
        print("SESSION ID:", session_id)

        async for event in self._graph.astream(self.initial_state, config, stream_mode="updates"):
            print("EVENT RUN:", event)
            print(f"this will be streamed: {Orchestrator.to_jsonable(event)}")
            yield Orchestrator.to_jsonable(event)   

        # Finalize state
        self.initial_state.final_content = getattr(self.initial_state, "last_output", "")
        yield {"type": "done", "content": self.initial_state.final_content}


    async def resume_stream(self, human_input: str, session_id: str):
        """
        Resume LangGraph execution after HITL interrupt.
        """

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 8,
        }

        print("GRAPH ID RESUME:", id(self._graph))
        print("CHECKPOINTER ID RESUME:", id(self._graph.checkpointer))
        print("SESSION ID:", session_id)
        print(f"Human Input: {human_input}")

        # -------------------------------
        # 🔹 DEBUG: check interrupted nodes before resume
        # -------------------------------
        interrupted = getattr(self._graph.checkpointer, "interrupted_nodes", None)
        print("Interrupted nodes BEFORE resume:", interrupted)

        resume_payload = {"human_response": human_input}
        print("Resume payload:", resume_payload)


        final_output = ""
        async for event in self._graph.astream(
            Command(resume={"human_response": human_input}),
            config,
            stream_mode="updates",
        ):
            print("EVENT RESUME:", event)
            json_event = Orchestrator.to_jsonable(event)
            print(f"RESUME STREAM: {json_event}")

            if "last_output" in json_event:
                final_output = json_event["last_output"]

            print("FINAL OUTPUT: ", final_output)

            yield json_event

        yield {"type": "done", "content": final_output}


    @staticmethod
    def to_jsonable(obj):
        """
        Recursively convert complex objects to JSON-safe structures.
        """

        # Primitive types
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        # datetime → ISO string
        if isinstance(obj, datetime):
            return obj.isoformat()

        # UUID → string
        if isinstance(obj, UUID):
            return str(obj)

        # Enum → value
        if isinstance(obj, Enum):
            return obj.value

        # Handle LangGraph Interrupt
        #
        #if isinstance(obj, Interrupt):
        #    return obj.value  # <-- THIS IS THE IMPORTANT PART

        # Handle LangGraph Interrupt safely
        if obj.__class__.__name__ == "Interrupt":
            return Orchestrator.to_jsonable(getattr(obj, "value", None))

        # list / tuple / set
        if isinstance(obj, (list, tuple, set)):
            return [Orchestrator.to_jsonable(item) for item in obj]

        # dict
        if isinstance(obj, dict):
            return {str(k): Orchestrator.to_jsonable(v) for k, v in obj.items()}

        # Pydantic v2
        if hasattr(obj, "model_dump"):
            return Orchestrator.to_jsonable(obj.model_dump())

        # Pydantic v1
        if hasattr(obj, "dict"):
            return Orchestrator.to_jsonable(obj.dict())


        # Dataclass (safe way)
        if hasattr(obj, "__dataclass_fields__"):
            return {
                k: Orchestrator.to_jsonable(getattr(obj, k))
                for k in obj.__dataclass_fields__
            }

        # Generic object → fallback to __dict__
        if hasattr(obj, "__dict__"):
            return Orchestrator.to_jsonable(vars(obj))

        # Last resort
        return str(obj)

    async def run1(self, user_intent: str, session_id: str, workspace_meta: dict) -> Dict[str, Any]:
        """
        Run the session through the LangGraph.
        Returns final session state.
        """

        # Get the initial State
        logger.info('Acquiring new state')
        self.initial_state = await self.core_engine.acquire_new_state(user_intent, session_id)
        logger.info(f"Start with an initial state: {self.initial_state}")

        self.initial_state.model_rebuild()

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
            "recursion_limit": 8  # Safety valve: Max 50 node transitions
        }

        iter = 0
        async for event in self._graph.astream(self.initial_state, config, stream_mode="updates"):
            iter = iter + 1
            first_key = list(event)[0]
            logger.info( "=====================================================================================================")
            logger.info(f" (R)   Iteration {iter}:   We completed {first_key} from graph.astream, and an event is emitted.     ")
            logger.info( "=====================================================================================================")

            logger.info(f"Event yield: {first_key}")

            # self.hitl_loop(event)


            # self.spinner_task()

            await self.event_bus.emit("graph_event", event)
            logger.info("Now running next iteration and waiting for graph_event response")

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

    def spinner_task(self):
        spinner = itertools.cycle(['-', '/', '|', '\\'])
        print("\rProcessing... ", end="")
        
        for _ in range(20): # Simulate a task
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            time.sleep(0.1)
            sys.stdout.write('\b') # Backspace to overwrite the character

    def hitl_loop(self, event: Any):

        for node_name, state_update in event.items():
            logger.console(f"\nNode: {node_name}")
            logger.console(f"state_update: {state_update}") 
            try: 
                workflow = state_update.get("workflow_metadata")
                if workflow and workflow.get("status"):
                    status = workflow.get("status")
                    if status == "SUSPENDED":
                        logger.console(f"\nUser Intent: {workflow.get("user_intent")}")
                        logger.console(f"Agent: {workflow.get("agent")}")
                        logger.console(f"Role: {workflow.get("role")}")
                        user_response = input("\n>>> Provide guidance: ")
            except Exception as e:
                logger.info(f"Exception Encountered: {e}")
 
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


