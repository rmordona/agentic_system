"""
StageGraph defines the execution topology for agents across stages.

It constructs a LangGraph where agents are nodes, stages define ordering,
and the stage_router determines progression and termination.

StageGraph does NOT execute skills or manage memory —
it only decides *what runs next*.
"""

from typing import Optional, Any, Dict, List
from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate

from runtime.agent_factory import AgentSchema, AgentRunner
from runtime.artifact_factory import ArtifactFactory
from runtime.graph.stage_state import StateSchema, AgentOutput, merge_reward_dicts
from runtime.tool_registry import ToolRegistry

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class StageGraph:

    def __init__(
        self,
        workspace_name: str,
        agent_registry,
        stage_registry,
        tool_registry,
        domain_manager,
        execution_mode: str = "stage_router",  # can be "sdd" for PipelineAdapter mode
        hitl_callback: Optional[Any] = None,
    ):
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        self.tool_registry = tool_registry
        self.domain_manager = domain_manager

        self.execution_mode = execution_mode
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
        logger.info(f"StageGraph initializing with channels: {list(self.channels.keys())}")

        # StateGraph
        self.graph = StateGraph(State, channels=self.channels)
        self._build_graph()

    # -------------------------------
    def _build_graph(self):
        # 1. Validate all stages have loaded agents
        logger.info(f"Validating all stages have loaded agents")
        for stage_name in self.stage_registry.list_stages():
            stage = self.stage_registry.get(stage_name)
            logger.info(f"Stage Name: {stage}")
            for agent_name in stage.allowed_agents:
                logger.info(f"Allowed agent: {agent_name}")
                if not self.agent_registry.exists(agent_name):
                    logger.error(
                        f"Stage '{stage_name}' requires agent '{agent_name}' "
                        f"but it is not loaded in the agent registry."
                    )
                    raise ValueError(
                        f"Stage '{stage_name}' requires agent '{agent_name}' "
                        f"but it is not loaded in the agent registry."
                    )

        # 2. Add agent nodes
        for agent in self.agent_registry.all():
            node_func = self._make_agent_node(agent)
            self.graph.add_node(agent.role, node_func)
        logger.info(f"Registered agent nodes added to graph: {list(self.graph.nodes.keys())}")

        # 3. Add stage router node with SDD support if pipeline_adapter is provided
        self._add_stage_router_node()
        #self._add_stage_router_node(pipeline_adapter=self.pipeline_adapter, execution_mode=self.execution_mode)
        logger.info(f"Stage Router added to graph with execution mode: {self.execution_mode}")

        # 4. Add edges: agents → stage_router, stage_router → next_agent / END
        self._add_edges()
        logger.info(f"Conditional Edges added to graph")

        # 5. Set entry point to stage_router
        self.graph.set_entry_point("stage_router")
        logger.info("Entry to graph now set: First stop is the 'stage_router'.")
        logger.info("StageGraph build complete. Entry point: 'stage_router'")


    def _make_agent_node(self, agent:AgentSchema):

        # Retrieve the system template generated during Agent Registration
        system_template = self.agent_registry.system_template

        # 1. Bind the agent (AgentSchema) to a runner (AgentRunner)
        runner = self.agent_registry.get_runner(agent)
        runner.set_system_template(system_template)

        async def agent_node(state: StateSchema) -> dict:
            stage_name = state["stage"]

            # 2. Initialize the Artifact/Suitcase
            # We pass the raw control string from the state
            factory = ArtifactFactory(state["artifact"])

            # 3. The CRITICAL STEP: Extract the specific task for THIS agent
            current_task = factory.get_next_task_for_stage(agent.role)

            if not current_task:
                logger.info(f"No pending tasks for {agent.role}. Skipping.")
                return {}
            
            # 4. Now let the agent run - take the specific task to hydrate the prompt
            proposal = await runner.run(state)
            '''
                task=current_task, 
                data_raw=state["data_raw"],
                data_type=state["data_type"]
            )
            '''

            # 4. Update the Suitcase (Mark task as complete)
            # The factory handles the regex to flip [ ] to [x]
            updated_control = factory.mark_task_complete(current_task)

            return {
                "control_raw": updated_control, # The updated suitcase
                "data_raw": proposal.new_data,    # The updated body
                "history_agents": [AgentOutput(...)]
            }

        return agent_node

    # -------------------------------
    '''
    def _make_agent_node(self, agent):
        async def agent_node(state: State) -> dict:
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)

            if agent.role not in stage.allowed_agents:
                return {}

            # Add the agent name to the state
            logger.info(f"Adding agent ({agent.role}) to runtime state")
            state["agent"] = agent.role

            logger.info(f"State: {state}")

            # Bind the node to an Agent Runner
            runner = AgentRunner(agent, self.tool_registry)

            # Prepare the artifact (SuiteCase) for the Agent
            artifact = ArtifactFactory()

            # Now let the agent run
            output = runner.run(artifact, state)

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
    '''

    # -------------------------------
    def _add_stage_router_node(self):
        """
        Stage router node with dual-mode support:
        - mode="sdd": use PipelineAdapter for dynamic stage routing
        - mode="stage_router": use original stage_registry routing
        """
        async def stage_router(state: State) -> dict:
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)
            executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])
            remaining = [a for a in stage.allowed_agents if a not in executed]

            # Run next agent if any remaining in current stage
            if remaining:
                next_agent = remaining[0]
                if next_agent not in self.graph.nodes:
                    raise ValueError(
                        f"StageRouter: Next agent '{next_agent}' is not a valid graph node!"
                    )
                return {"next_agent": next_agent}

            # 2Stage exit → determine next stage
            if self.execution_mode == "sdd":
                artifact = state.get("artifact", {"current_plan": []})
                decision = self.stage_registry.get_next_stage(artifact)
                next_stage_name = decision.get("next_stage")
                allowed_agents = decision.get("allowed_agents", [])

                # Terminal stage or HITL required
                if not next_stage_name or decision.get("hitl_required"):
                    return {"done": True}

                # Update artifact back in state
                state["artifact"] = artifact

                # Pick first agent of next stage
                next_agent = allowed_agents[0] if allowed_agents else None
                return {"stage": next_stage_name, "next_agent": next_agent}

            else:
                # Fallback: original stage_router behavior
                logger.info("What the????????????????????????????????")
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

            # 3️⃣ Default: done
            return {"done": True}

        self.graph.add_node("stage_router", stage_router)

    # -------------------------------
    def _add_edges(self):
        all_roles = list(self.agent_registry.roles())

        logger.info(f"Roles: {all_roles}")

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
