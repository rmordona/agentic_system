from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from typing import Optional, Any
from runtime.logger import AgentLogger


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

        # ✅ Channels defined ONCE
        self.channels = {
            "stage": LastValue(str),
            "done": LastValue(bool),

            # Stream of agent execution events
            "agent_events": Topic(dict),

            # Aggregated execution history per stage
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

        self.graph = StateGraph(dict, channels=self.channels)

        self._build_graph()

        global logger
        logger = AgentLogger.get_logger(workspace_name, component="stage_graph")

    # ------------------------------------------------------------------

    def _build_graph(self):
        self._add_stage_router_node()

        for agent in self.agent_registry.all():
            self._add_agent_node(agent)
            self.graph.add_edge(agent.role, "stage_router")

        self.graph.set_entry_point("stage_router")

    # ------------------------------------------------------------------

    def _add_agent_node(self, agent):
        async def agent_node(state, agent=agent):
            output = await agent.run(state)

            return {
                "agent_events": {
                    "stage": state["stage"],
                    "agent": agent.role,
                    "output": output,
                },
                "executed_agents_per_stage": {
                    state["stage"]: [agent.role]
                },
            }

        self.graph.add_node(agent.role, agent_node)

    # ------------------------------------------------------------------

    def _add_stage_router_node(self):
        def stage_router(state):
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)

            executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])

            # 1️⃣ Schedule agents
            for agent_role in stage.allowed_agents:
                if agent_role not in executed:
                    return agent_role

            # 2️⃣ Exit condition
            if stage.should_exit(state):
                stage.on_exit(state)

                if stage.terminal:
                    return END

                return {"stage": stage.next_stages[0]}

            # 3️⃣ Loop
            return "stage_router"

        self.graph.add_node("stage_router", stage_router)

    # ------------------------------------------------------------------

    def compile(self):
        return self.graph.compile()
