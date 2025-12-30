from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

# Short-Term memory level schemas
# - Schema memory structures For Agents
# - When saving memory, it must conform to one of these memory shapes.”
class ProposalMemory(BaseModel):
    session_id: str
    task: str
    agent: str
    stage: str
    input_context: List[Dict[str, Any]]  # Task + conversation history seen by agent
    output: Dict[str, Any]

class CritiqueMemory(BaseModel):
    session_id: str
    task: str
    agent: str
    stage: str
    input_context: List[Dict[str, Any]]  # Optimistic proposals (what critic saw)
    output: Dict[str, Any]

class SynthesizerMemory(BaseModel):
    session_id: str
    task: str
    agent: str  # will always be "synthesizer"
    stage: str
    input_context: Dict[str, Any]  # combined optimistic + critic
    decision: Dict[str, Any]         # final recommendation

# This is the SessionMemory Schema: Long-Term memory level schemas
# - Semantic Schema memory structures For Orchestrator
class SemanticMemory(BaseModel):
    """
    Stores a compacted, semantic-level summary of multiple agent outputs
    for a given session and task, with a category for semantic classification.
    """
    session_id: str               # session identifier
    task: str                     # task associated with the memories
    stage: str = "conversation"   # stage where compaction occurs (values are either conversation or summary)
    content: Dict[str, Any]       # the actual compacted summary text
    category: str                 # e.g., "intent", "preference", "constraint", "fact"
    notes: Optional[str] = None   # optional field for metadata or annotations

# This is the Summarized Episodic Memory
# - Schema memory structures summarized from accumulated synthesizer memory
class EpisodicMemory(BaseModel):
    """
    Stores a compacted, semantic-level summary of multiple agent outputs
    for a given session and task, with a category for semantic classification.
    """
    session_id: str
    task: str                   # task associated with the memories
    agent: str                  # will always be "synthesizer"
    stage: str                  # stage where compaction occurs (values are either conversation or summary)
    caregory: str = "intent"    # e.g., "intent", "preference", "constraint", "fact"
    summary: Dict[str, Any]     # he actual compacted summary text


# Required in Pydantic v2
ProposalMemory.model_rebuild()
CritiqueMemory.model_rebuild()
SynthesizerMemory.model_rebuild()
SemanticMemory.model_rebuild()
EpisodicMemory.model_rebuild()

