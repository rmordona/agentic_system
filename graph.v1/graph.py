"""
graph.py

Defines the LangGraph execution topology for the agentic LLM system.

Key properties:
- Agents are graph nodes
- Execution is controlled by LangGraph (not the orchestrator)
- Parallelism is declarative via fan-out routing
- Stages restrict which agents may execute
- The graph is dynamically built from registries
- No hard-coded DAGs or sequential workflows

This module must remain:
- Stateless
- Deterministic
- Free of business logic
"""

from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
from graph.state import State,  AgentOutput, set_default_channel, merge_reward_dicts
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate

def make_agent_node(agent, channel, stage_registry):
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
            '''
            return {
                "executed_agents_per_stage" : { stage_name : executed },
                "history_agents": {
                    "stage": stage_name,
                    "role": agent.role,
                    "output": output,
                }
            }
            '''

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

def build_graph(agent_registry, stage_registry, hitl_callback=None):
    """
    Build and compile a LangGraph execution graph with stage routing and optional HITL.
    """

    # ------------------------------------------------------------------
    # 1. Initialize the graph with a shared state schema
    # ------------------------------------------------------------------
    graph = StateGraph(State)

    channels: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 2. Register agent nodes dynamically
    # ------------------------------------------------------------------
    for agent in agent_registry.all():
        # Set up channel for agent
        channels[agent.role] = Topic(agent.role) # set_default_channel(agent.role)

        # Create node using factory
        node = make_agent_node(agent,  channels[agent.role], stage_registry)

        # Register node in the graph
        graph.add_node(
                agent.role, node, 
                channel={
                    "history_agents": Topic(list),
                    "rewards" : BinaryOperatorAggregate(dict, merge_reward_dicts),
                    "executed_agents_per_stage" : LastValue(dict)
                }
        )

    # ------------------------------------------------------------------
    # 3. Stage router node (controls agent selection per stage)
    # ------------------------------------------------------------------
    async def stage_router(state: State):
        stage_name = state["stage"]
        current_stage = stage_registry.get(stage_name)

        executed = state.get("executed_agents_per_stage", {}).get(stage_name, [])
        remaining = [a for a in current_stage.allowed_agents if a not in executed]

        print("STAGE ROUTER")
        print("Stage:", stage_name)
        print("Executed:", executed)
        print("Remaining:", remaining)

        # HITL override (highest priority)
        if hitl_callback:
            decision = await hitl_callback(state, stage_name)
            if decision == "skip_stage":
                remaining = []
            elif isinstance(decision, str) and decision not in executed:
                return {"next_agent": decision}


        # Stage exit condition
        if current_stage.should_exit(state) or not remaining:
            next_stage = stage_registry.next_stage(stage_name)

            if next_stage:

                next_stage_obj = stage_registry.get(next_stage)

                if not next_stage_obj.allowed_agents:
                    # No agents. This is a terminal stage
                    return {
                        "stage": next_stage,
                        "done": True,
                    }

                next_agent = next_stage_obj.allowed_agents[0]
                print(f"ADVANCE STAGE {stage_name} → {next_agent}")
                return {
                    "stage": next_stage,
                    "next_agent": next_agent,
                    # "history_agents": state.get("history_agents", []),
                    #"executed_agents_per_stage": state.get("executed_agents_per_stage", {})
                }

            print("GRAPH DONE")
            return {"done": True}

        # Normal agent routing
        return {"next_agent": remaining[0]}

    graph.add_node("stage_router", stage_router)

    # ------------------------------------------------------------------
    # 4. Routing logic (Conditional Edges)
    # ------------------------------------------------------------------
    all_roles = list(agent_registry.roles())
    # Each agent -> stage_router
    # After an agent completes, it routes back to the router if not done
    for role in all_roles:
        graph.add_conditional_edges(
            role,
            lambda s: ["stage_router"] if not s.get("done") else [END],
            {
                "stage_router": "stage_router",
                END: END,
            },
        )

    graph.add_conditional_edges(
        "stage_router",
        lambda s: [s["next_agent"]] if s.get("next_agent") else [END],
        {role: role for role in all_roles} | {END: END},
    )
    
    # ------------------------------------------------------------------
    # 5. Entry point
    # ------------------------------------------------------------------
    first_stage_name = stage_registry._order[0]
    first_stage = stage_registry.get(first_stage_name)
    if not first_stage.allowed_agents:
        raise ValueError(f"Stage '{first_stage_name}' has no allowed agents.")

    graph.set_entry_point("stage_router")

    # ------------------------------------------------------------------
    # 6. Compile
    # ------------------------------------------------------------------
    return graph.compile()
