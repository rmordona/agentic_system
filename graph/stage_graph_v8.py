from typing import Optional, Any, Dict, List

from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate

from runtime.logger import AgentLogger
from graph.state import State, AgentOutput


class StageGraph:
    """
    Canonical LangGraph-based stage orchestrator.

    Design principles:
    - Routers RETURN ROUTES ONLY (string | END)
    - State is mutated ONLY via channel deltas
    - Agents are stateless, deterministic workers
    - Stage routing is centralized and explicit
    """

    # ------------------------------------------------------------------
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

        # -------------------------------
        # Channels define merge semantics
        # -------------------------------
        self.channels = {
            # Current stage name
            "stage": LastValue(str),

            # Workflow termination flag
            "done": LastValue(bool),

            # Append-only agent execution history
            "history_agents": Topic(list),

            # { stage_name: [agent_role, ...] }
            "executed_agents_per_stage": BinaryOperatorAggregate(
                dict,
                lambda acc, x: {
                    **acc,
                    **{
                        stage: acc.get(stage, []) + agents
                        for stage, agents in x.items()
                    },
                },
            ),
        }

        self.graph = StateGraph(State, channels=self.channels)
        self._build_graph()

        global logger
        logger = AgentLogger.get_logger(
            workspace_name,
            component="stage_graph",
        )

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def _build_graph(self):
        self._add_agent_nodes()
        self._add_stage_router_node()
        self._add_edges()

        # Entry point is always the router
        self.graph.set_entry_point("stage_router")

    # ------------------------------------------------------------------
    # Agent nodes
    # ------------------------------------------------------------------
    def _add_agent_nodes(self):
        """
        Each agent:
        - Executes exactly once per stage
        - Returns ONLY state deltas
        - Never performs routing or stage transitions
        """
        for agent in self.agent_registry.all():

            async def agent_node(state: State, agent=agent) -> Dict:
                stage_name = state["stage"]

                # Safety check (router should already enforce this)
                stage = self.stage_registry.get(stage_name)
                if agent.role not in stage.allowed_agents:
                    return {}

                # Execute agent
                output = await agent.run(state)

                # Return deltas only
                return {
                    "executed_agents_per_stage": {
                        stage_name: [agent.role]
                    },
                    "history_agents": [
                        AgentOutput(
                            stage=stage_name,
                            role=agent.role,
                            output=output,
                        )
                    ],
                }

            self.graph.add_node(agent.role, agent_node)

    # ------------------------------------------------------------------
    # Stage router
    # ------------------------------------------------------------------
    def _add_stage_router_node(self):
        """
        The ONLY node allowed to:
        - Decide which agent runs next
        - Decide when to exit a stage
        - Decide when the workflow ends

        This node NEVER mutates state directly.
        """

        async def stage_router(state: State):
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)

            executed = state.get(
                "executed_agents_per_stage", {}
            ).get(stage_name, [])

            remaining = [
                agent for agent in stage.allowed_agents
                if agent not in executed
            ]

            logger.debug(
                f"[Router] stage={stage_name} "
                f"executed={executed} remaining={remaining}"
            )

            # 1️⃣ Run remaining agents in this stage
            if remaining:
                return remaining[0]  # MUST be string

            # 2️⃣ Stage exit check
            if stage.should_exit(state):
                next_stage = self.stage_registry.next_stage(stage_name)

                if not next_stage:
                    logger.info("No next stage. Ending workflow.")
                    return END

                # Advance stage via state delta
                logger.info(
                    f"Advancing stage: {stage_name} → {next_stage}"
                )
                return next_stage

            # 3️⃣ Fallback (should not usually happen)
            return END

        self.graph.add_node("stage_router", stage_router)

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------
    def _add_edges(self):
        all_roles = list(self.agent_registry.roles())
        all_stage_names = list(self.stage_registry.names)

        # Agents always go back to the router
        for role in all_roles:
            self.graph.add_edge(role, "stage_router")

        # Router routes to:
        # - agent roles
        # - stage names (stage advancement)
        # - END
        routing_targets = {
            **{role: role for role in all_roles},
            **{stage: "stage_router" for stage in all_stage_names},
            END: END,
        }

        self.graph.add_conditional_edges(
            "stage_router",
            lambda route: [route],
            routing_targets,
        )

    # ------------------------------------------------------------------
    def compile(self):
        return self.graph.compile()

