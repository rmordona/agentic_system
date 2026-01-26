##################################################################
# THE TRI-PLANE ARCHITECTURE
# -------------------------
# Purpose:
#   The Tri-Plane Architecture defines a strict separation of concerns between
#   control, execution, and data in an agentic system.
#
#   It ensures that reasoning, action, and evidence are isolated, auditable,
#   and composable — enabling safe multi-agent collaboration and replay.
#
# Mental Model:
#   Think of execution as a continuous cycle:
#
#     Artifact (Control) → Agent (Decision) → Tool (Execution) → Data (Evidence)
#
#   - The Artifact dictates intent, constraints, and progress.
#   - The Agent reasons and decides what action to take next.
#   - The Tool performs the concrete action.
#   - The Data records the outcome of that action.
#
#   Each plane evolves independently but remains causally linked.
#
# ----------------------------------------------------------------
# Plane Definitions
#
# Control Plane (control_raw):
#   - Canonical source of truth for intent and workflow state.
#   - Human-readable and agent-readable.
#   - Governs what *should* happen.
#
#   Key Question:
#     "Is the task 'Book Flight' checked off yet?"
#
# Execution Plane (tool_raw):
#   - Immutable record of concrete actions taken.
#   - Captures tool invocations, parameters, and execution results.
#   - Governs what *was done*.
#
#   Key Question:
#     "What API parameters did we send to Delta at 2 PM?"
#
# Data Plane (data_raw):
#   - Immutable record of domain-specific outcomes and evidence.
#   - Stores business-level results derived from execution.
#   - Governs what *was produced*.
#
#   Key Question:
#     "What is the final confirmation number for the user?"
#
# ----------------------------------------------------------------
# Architectural Guarantees:
#   - No plane may directly mutate another plane.
#   - Control logic MUST NOT depend on tool or data internals.
#   - All planes are append-only for auditability.
#   - Replay and forensic reconstruction are always possible.
#
# In short:
#   Control decides.
#   Execution acts.
#   Data proves.
##################################################################


import operator
from pydantic import BaseModel
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated, Literal, Optional
from langgraph.channels import Topic, LastValue, BinaryOperatorAggregate
from langgraph.graph.message import add_messages  # optional


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

class StateSchema(BaseModel):

    # Session Id
    session_id: str

    # Control Plane
    control_raw: ArtifactSchema     

    # Data Plane (Domain Specific) - See Domain Manager
    data_raw: Dict[str, List[DataEnvelope]]   

    # Tool Plane  
    tool_raw: Dict[str, List[ToolEnvelope]]   

    # User Intent
    user_intent: str = None

    # Task metadata
    task: str

    # Stage management and control (only orchestrator updates)
    # - Control-plane fields
    # - Exactly one writer per step
    # - Matches your “stage-driven graph” design
    # - Prevents concurrent updates
    #stage: Annotated[str, LastValue(str)]
    #done: Annotated[bool, LastValue(bool)]
    agent: str
    stage: str
    done: bool

    # History: collect all agent outputs per step (note this is agent output, becomes history)
    # Multi-agent outputs (fan-in safe)
    # - Control-plane fields
    # - Exactly one writer per step
    # - Matches your “stage-driven graph” design
    # - Prevents concurrent updates
    #history_agents: Annotated[List[AgentOutput], Topic(AgentOutput)]
    history_agents: List[AgentOutput] = []

    # Executed Agents per Stage
    #executed_agents_per_stage: Annotated[ Dict[str, List[str]],LastValue(dict)]
    executed_agents_per_stage: Dict[str, List[str]] = {}

    # Allows any other metadata
    workflow_metadata : Dict[str,str] = {}

    class Config:
        arbitrary_types_allowed = True  # allows ArtifactSchema inside


