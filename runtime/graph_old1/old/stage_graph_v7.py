'''
On channels:

"stage": LastValue(str)
- This stores the current stage name.
- LastValue ensures only the latest value wins.
- Example: If the stage router moves from "ideation" → "evaluation", this channel updates to "evaluation".

"done": LastValue(bool)
- Indicates whether the workflow is complete.
- Only the latest value matters: True or False.

"agent_events": Topic(dict)
- This is a fan-in channel that collects multiple events from agents.
- Each agent node appends its execution result here.
- Example: After the optimistic agent runs:

"executed_agents_per_stage": BinaryOperatorAggregate(...)
-Tracks which agents have already executed per stage.
- The reducer function merges incoming updates with the existing state:
- This is how the stage router knows which agents have already run.
- It’s not mapping every agent to every stage—it’s just recording executions dynamically as they happen.
'''

from langgraph.graph import StateGraph, END
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from typing import Optional, Any
from runtime.logger import AgentLogger
from graph.state import State,  AgentOutput, set_default_channel, merge_reward_dicts

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

        # Channels:  Each channel defines a state key and how
        # updates to that key are merged by LangGraph
        self.channels = {
            "stage": LastValue(str),
            "done": LastValue(bool),
            "history_agents": Topic(dict),
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

        #self.channels: Dict[str, Any] = {}

        self.graph = StateGraph(State, channels=self.channels)
        self._build_graph()

        global logger
        logger = AgentLogger.get_logger(workspace_name, component="stage_graph")

    # ------------------------------------------------------------------
    def _build_graph(self):
        # 1. Create agent nodes
        for agent in self.agent_registry.all():
            self.channels[agent.role] = Topic(agent.role)
            self._add_agent_node(agent, self.channels[agent.role] )

        # 2. Stage router node
        self._add_stage_router_node()

        # 3. Conditional edges
        self._add_conditional_edges()

        # 4. Entry point
        first_stage_name = self.stage_registry._order[0]
        first_stage = self.stage_registry.get(first_stage_name)
        if not first_stage.allowed_agents:
            raise ValueError(f"Stage '{first_stage_name}' has no allowed agents.")

        self.graph.set_entry_point("stage_router")

    # ------------------------------------------------------------------

    def _add_agent_node(agent, channel, stage_registry):
        # langgraph invoked from langraph/_internal/_runnable.py
        # e.g. ret = await node.ainvoke(state_snapshot)
        async def agent_node(state: State) -> dict:
            current_stage = stage_registry.get(state["stage"])

            # Safety gate
            if agent.role not in current_stage.allowed_agents:
                return {}

            # Run agent
            output = await agent.run(state)

            # Record Execution - this is only to compose the executed which will be returned
            # given that the state is just snapshot and is not globally mutable
            stage_name = state["stage"]
            per_stage = state.setdefault("executed_agents_per_stage", {})
            executed = per_stage.setdefault(stage_name, [])

            if agent.role not in executed:
                executed.append(agent.role)

            print("Here in agent_node:")
            print(f"Executed: ", executed)
            
            print("Just set the stage where node is executed ...")
            print("DEBUG channel:", channel, type(channel))
            print("DEBUG TopicChannel:", Topic)

            # *************** BEGIN OF DEBUG


            print("Agent node state:")
            print(f"State:", state)

            print("We are in Agent node .... ")
            print(f"stage: {stage_name}")
            print(f"executed: ", executed )

            # Already executed agents in this stage
            executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])

            print("in Agent node , which agents are executed")
            print(f"executed: ", executed )

            # *************** END OF DEBUG

            # Channel-aware output
            # Return deltas so langgraph can merge them via channels.
            if isinstance(channel, Topic):
                # TopicChannel expects a dict delta
                print("Got here for topic channel")
                # Return node delta including executed info
                # langraph merges via:  state[key].append(new_value)
                # from langgraph/pregel/_write.py (_assemble_writes)
                # goes back to graph.astream. From there, entry point is back to stage_router
                # upon entry, stage_router should have seen the merge of the nodes' returned dict
                
                return {
                    "executed_agents_per_stage" : { stage_name : executed },
                    "history_agents" : 
                    [  AgentOutput(
                            stage = stage_name,
                            role = agent.role,
                            output = output
                        ) ] 
                }

            elif isinstance(channel, LastValue):
                # LastValue expects a dict delta
                # langraph merges via:  state[key] = new_value
                print("Got here for lastvalue channel")
                return { "stage" : agent.role }
            elif isinstance(channel, BinaryOperatorAggregate):
                # Example: voting / winner selection
                # langraph merges via:  state[key] = reducer(state[key], new_value)
                print("Got here for binop channel")
                return { "winner": agent.role }

            print("otherwise here then ...")

    
            # Ensure output is a dict
            if not isinstance(output, dict):
                output = {"result": output}

            return {}

        return agent_node

        self.graph.add_node(agent.role, agent_node,
                channel={
                    "history_agents": Topic(list),
                    "rewards" : BinaryOperatorAggregate(dict, merge_reward_dicts),
                    "executed_agents_per_stage" : LastValue(dict)
                }
        )



    # ------------------------------------------------------------------
    def _add_stage_router_node(self):

        async def stage_router(state: State):
            stage_name = state["stage"]
            stage = self.stage_registry.get(stage_name)

            executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])
            remaining = [a for a in stage.allowed_agents if a not in executed]

            # Run next agent
            if remaining:
                return {"next_agent": remaining[0]}

            # Stage exit
            if stage.should_exit(state):
                next_stage = self.stage_registry.next_stage(stage_name)

                if not next_stage:
                    return {"done": True}

                next_stage_obj = self.stage_registry.get(next_stage)
                next_agent = next_stage_obj.allowed_agents[0]

                return {
                    "stage": next_stage,
                    "next_agent": next_agent,
                }

            return {"done": True}

        self.graph.add_node("stage_router", stage_router)

   # ------------------------------------------------------------------
    def _add_conditional_edges(self):
        all_roles = list(self.agent_registry.roles())

        # Agent → stage_router / END
        #for role in all_roles:
        #    self.graph.add_conditional_edges(
        #        role,
        #        lambda s: ["stage_router"] if not s.get("done") else [END],
        #        {"stage_router": "stage_router", END: END},
        #    )

        for role in all_roles:
            self.graph.add_edge(role, "stage_router")

        # stage_router → next_agent / END
        self.graph.add_conditional_edges(
            "stage_router",
            lambda s: [s["next_agent"]] if s.get("next_agent") else [END],
            {role: role for role in all_roles} | {END: END},
        )


    # ------------------------------------------------------------------
    def compile(self):
        return self.graph.compile()
