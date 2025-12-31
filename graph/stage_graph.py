# stage_graph.py

from typing import Optional, Any, Dict, List
from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from runtime.logger import AgentLogger
from graph.state import State, AgentOutput, merge_reward_dicts

class StageGraph:

    def __init__(
        self,
        workspace_name: str,
        agent_registry,
        stage_registry,
        hitl_callback: Optional[Any] = None,
    ):
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        self.hitl_callback = hitl_callback

        # Channels
        self.channels = {
            "stage": LastValue(str),
            "done": LastValue(bool),
            "history_agents": Topic(list),
            "executed_agents_per_stage": BinaryOperatorAggregate(
                dict,
                lambda acc, x: {
                    **acc,
                    **{stage: acc.get(stage, []) + agents for stage, agents in x.items()},
                },
            ),
            "rewards": BinaryOperatorAggregate(dict, merge_reward_dicts),
        }

        # Logger
        self.logger = AgentLogger.get_logger(workspace_name, component="stage_graph")
        self.logger.info(f"StageGraph initializing with channels: {list(self.channels.keys())}")

        # StateGraph
        self.graph = StateGraph(State, channels=self.channels)
        self._build_graph()

    # -------------------------------
    def _build_graph(self):
        # 1. Validate all stages have loaded agents
        for stage_name in self.stage_registry.list_stages():
            stage = self.stage_registry.get(stage_name)
            for agent_role in stage.allowed_agents:
                if not self.agent_registry.exists(agent_role):
                    raise ValueError(
                        f"Stage '{stage_name}' requires agent '{agent_role}' "
                        f"but it is not loaded in the agent registry."
                    )

        # 2. Add agent nodes
        for agent in self.agent_registry.all():
            node_func = self._make_agent_node(agent)
            self.graph.add_node(agent.role, node_func)
        self.logger.info(f"Registered agent nodes: {list(self.graph.nodes.keys())}")

        # 3. Add stage router node
        self._add_stage_router_node()

        # 4. Add edges: agents → stage_router, stage_router → next_agent / END
        self._add_edges()

        # 5. Set entry point to stage_router
        self.graph.set_entry_point("stage_router")
        self.logger.info("StageGraph build complete. Entry point: 'stage_router'")

    # -------------------------------
    def _make_agent_node(self, agent):
        async def agent_node(state: State) -> dict:
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)

            if agent.role not in stage.allowed_agents:
                return {}

            # Run agent
            output = await agent.run(state)

            # Track executed agents
            per_stage = state.setdefault("executed_agents_per_stage", {})
            executed = per_stage.setdefault(stage_name, [])
            if agent.role not in executed:
                executed.append(agent.role)

            return {
                "executed_agents_per_stage": {stage_name: executed},
                "history_agents": [
                    AgentOutput(stage=stage_name, role=agent.role, output=output)
                ],
            }

        return agent_node

    # -------------------------------
    def _add_stage_router_node(self):
        async def stage_router(state: State) -> dict:
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)
            executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])
            remaining = [a for a in stage.allowed_agents if a not in executed]

            # Run next agent if any remaining
            if remaining:
                next_agent = remaining[0]
                if next_agent not in self.graph.nodes:
                    raise ValueError(
                        f"StageRouter: Next agent '{next_agent}' is not a valid graph node!"
                    )
                return {"next_agent": next_agent}

            # Stage exit
            if stage.should_exit(state):
                next_stage_name = self.stage_registry.next_stage(stage_name)
                if not next_stage_name:
                    return {"done": True}

                next_stage = self.stage_registry.get(next_stage_name)
                next_agent = next_stage.allowed_agents[0]
                if next_agent not in self.graph.nodes:
                    raise ValueError(
                        f"StageRouter: First agent of next stage '{next_agent}' not in graph nodes!"
                    )

                return {"stage": next_stage_name, "next_agent": next_agent}

            return {"done": True}

        self.graph.add_node("stage_router", stage_router)

    # -------------------------------
    def _add_edges(self):
        all_roles = list(self.agent_registry.roles())

        # Agent → stage_router
        for role in all_roles:
            self.graph.add_edge(role, "stage_router")

        # stage_router → next_agent / END
        self.graph.add_conditional_edges(
            "stage_router",
            lambda s: [s["next_agent"]] if s.get("next_agent") else [END],
            {role: role for role in all_roles} | {END: END},
        )

    # -------------------------------
    def compile(self):
        return self.graph.compile()
