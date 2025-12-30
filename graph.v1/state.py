
"""
state.py

Defines the global state schema for the agentic LLM system using LangGraph channels.

Channels:
- Topic: Collect multiple agent outputs per stage
- LastValue: Store authoritative values (winner, stage)
- BinaryOperatorAggregate: Aggregate numeric rewards

Example of agent returning the state:

# Optimistic Agent
return {
    "history": [{
        "agent": self.role,
        "output": optimistic_analysis
    }],
    "rewards": {
        self.role: 0.7
    }
}

# Critic Agent
return {
    "history": [{
        "agent": self.role,
        "output": critique
    }],
    "rewards": {
        self.role: 0.8
    }
}

# Synthesizer Agent
return {
    "decision": {
        "summary": "...",
        "decision": "continue",
        "rationale": "..."
    }
}
"""

import operator
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated, Literal, Optional
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from langgraph.graph.message import add_messages  # optional

'''
from langgraph.graph.reducer import reducer

def history_agents_reducer(
    old: List["AgentOutput"] | None,
    new: "AgentOutput" | List["AgentOutput"] | None,
):
    if old is None:
        old = []
    if new is None:
        return old
    if isinstance(new, list):
        return old + new
    return old + [new]
'''



def merge_reward_dicts(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {
        k: a.get(k, 0.0) + b.get(k, 0.0)
        for k in set(a) | set(b)
    }

def set_default_channel(key: str):
    """
    Decide which channel type to use for a given state key.

    This is the SINGLE source of truth for state semantics.
    """

    # Multi-writer, fan-in safe (event-driven)
    if key in {"history", "tool_events"}:
        return TopicChannel(list)

    # Aggregation semantics (critic vs optimistic rewards)
    if key == "rewards":
        return BinaryOperatorAggregate(
            dict,
            lambda a, b: {
                k: a.get(k, 0) + b.get(k, 0)
                for k in set(a) | set(b)
            },
        )

    # Single-writer, last-write-wins (control plane)
    return LastValue(object)


# See main.py, how role is the same as the agent name
class AgentOutput(TypedDict):
    stage: str
    role: str
    output: Any

class ToolCall(TypedDict):
    agent: str
    tool: str
    args: Dict[str, Any]
    result: Any



class State(TypedDict):

    # Session Id
    session_id: str

    # Task metadata
    task: str


    # Stage management and control (only orchestrator updates)
    # - Control-plane fields
    # - Exactly one writer per step
    # - Matches your “stage-driven graph” design
    # - Prevents concurrent updates
    #stage: Annotated[str, LastValue(str)]
    #done: Annotated[bool, LastValue(bool)]
    stage: str
    done: bool

    # History: collect all agent outputs per step (note this is agent output, becomes history)
    # Multi-agent outputs (fan-in safe)
    # - Control-plane fields
    # - Exactly one writer per step
    # - Matches your “stage-driven graph” design
    # - Prevents concurrent updates
    #history_agents: Annotated[List[AgentOutput], Topic(AgentOutput)]
    history_agents: List[AgentOutput]

    # Rewards: aggregate numeric reward values from multiple agents
    # Dictates the scoring for reward.
    #rewards: Annotated[dict[str, float], BinaryOperatorAggregate(dict, merge_reward_dicts)]
    rewards: dict[str, float]

    # Decision: Synthesizer output, only one winner per step
    # Dictates the winner (not score)
    # - Arbitration result
    # - Single authority (synthesizer)
    # - LastValue enforces exclusivity
    #winner: Annotated[dict, LastValue(dict)]
    winner: dict

    # Final authoritative decision (synthesizer only)
    # - Final control-plane output
    # - Used by orchestrator / stages
    # - Safe for routing and termination
    #decision: Annotated[Dict[str, Any], LastValue(dict)]
    decision: dict

    # Executed Agents per Stage
    #executed_agents_per_stage: Annotated[ Dict[str, List[str]],LastValue(dict)]
    executed_agents_per_stage: Dict[str, List[str]]


