from dataclasses import dataclass, field
from typing import Optional, List, Generic, TypeVar, Dict, Any, Literal
from datetime import datetime, UTC, timezone

DomainType = TypeVar("DomainType")

@dataclass
class DataEnvelope(Generic[DomainType]):
    tool: str
    type: str
    version: str
    producer: str
    stage: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: DomainType | None = None
    checksum: Optional[str] = None
    references: List[str] = field(default_factory=list)

@dataclass
class ToolEnvelope(Generic[DomainType]):
    id: str
    tool_name: str
    tool_version: Optional[str] = None
    agent_role: Optional[str] = None
    stage_name: Optional[str] = None
    intent: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None
    success: bool = False
    governance_policy: Dict[str, Any] = field(default_factory=dict)
