from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue
from graph.state import State
from runtime.logger import AgentLogger

class StageGraph:
    """
    Encapsulates a LangGraph state graph for dynamic stages and agents.
    """
    def __init__(self, workspace_name: str, agent_registry, stage_registry, hitl_callback: Optional[Any] = None):
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        self.hitl_callback = hitl_callback

        self.graph = StateGraph(State)
        self.channels = {}
        self._build_graph()

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(workspace_name, component=f"state_graph")

    def _build_graph(self):
        # 1. Create agent nodes
        for agent in self.agent_registry.all():
            self.channels[agent.role] = Topic(agent.role)
            self._add_agent_node(agent)

        # 2. Stage router node
        self._add_stage_router_node()

        # 3. Conditional edges
        self._add_conditional_edges()

        # 4. Entry point
        self.graph.set_entry_point("stage_router")

    def _add_agent_node(self, agent):
        async def agent_node(state: State, agent=agent):
            stage = state["stage"]
            current_stage = self.stage_registry.stage_map[stage]

            if agent.role not in current_stage.get("allowed_agents", []):
                return {}

            output = await agent.run(state)

            executed = state.setdefault("executed_agents_per_stage", {}).setdefault(stage, [])
            if agent.role not in executed:
                executed.append(agent.role)

            return {agent.role: output, "executed_agents_per_stage": {stage: executed}}

        self.graph.add_node(
            agent.role,
            agent_node,
            channel={
                "executed_agents_per_stage": LastValue(dict),
                agent.role: Topic(list)
            }
        )

    def _add_stage_router_node(self):
        async def stage_router_node(state: State):
            stage = state["stage"]
            next_stage = self.stage_registry.next_stage(state)
            if next_stage is None:
                return {"done": True}
            else:
                next_agents = self.stage_registry.allowed_agents(next_stage)
                return {"stage": next_stage, "next_agent": next_agents[0] if next_agents else None}

        self.graph.add_node("stage_router", stage_router_node)

    def _add_conditional_edges(self):
        all_roles = list(self.agent_registry.roles())

        # Agent → stage_router / END
        for role in all_roles:
            self.graph.add_conditional_edges(
                role,
                lambda s: ["stage_router"] if not s.get("done") else [END],
                {"stage_router": "stage_router", END: END},
            )

        # stage_router → next_agent / END
        self.graph.add_conditional_edges(
            "stage_router",
            lambda s: [s["next_agent"]] if s.get("next_agent") else [END],
            {role: role for role in all_roles} | {END: END},
        )

    def compile(self):
        """
        Finalize the graph for execution.
        """
        return self.graph.compile()
