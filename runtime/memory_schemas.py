from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union

class GenericMemory(BaseModel):
    data: Dict[str, Any]

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
    key_namespace: Optional[tuple]                  # This includes session_id, agent, stage, namespace
    task: str                                        # This includes user message
    summary: Dict[str, Any]                          # he actual compacted summary text
    category: Optional[str]                          # e.g., "intent", "preference", "constraint", "fact"
    documents: Optional[Sequence[str]]               # Any document
    metadatas: Optional[Sequence[Dict[str, Any]]]    # Any Metadata
    annotations: Optional[Dict[str, Any]]            # optional field for metadata or annotations

# This is the Summarized Episodic Memory
# - Schema memory structures summarized from accumulated synthesizer memory
class EpisodicMemory(BaseModel):
    """
    Stores a compacted, semantic-level summary of multiple agent outputs
    for a given session and task, with a category for semantic classification.
    """
    key_namespace: Optional[tuple]                   # This includes session_id, agent, stage, namespace
    task: str                                        # This includes user message
    summary: Dict[str, Any]                          # he actual compacted summary text
    category: Optional[str]                          # e.g., "intent", "preference", "constraint", "fact"
    documents: Optional[Sequence[str]]               # Any document
    metadatas: Optional[Sequence[Dict[str, Any]]]    # Any Metadata
    annotations: Optional[Dict[str, Any]] = None     # optional field for metadata or annotations


# Required in Pydantic v2
ProposalMemory.model_rebuild()
CritiqueMemory.model_rebuild()
SynthesizerMemory.model_rebuild()
SemanticMemory.model_rebuild()
EpisodicMemory.model_rebuild()

