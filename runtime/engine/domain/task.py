from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, UTC, timezone

INIT_TASK = "--init--"

@dataclass
class Task:
    id: str
    description: str
    stage: str
    execution: Literal["tool", "llm"] = "tool"
    tool_name: str = ""
    depends_on: List[str] = field(default_factory=list)
    status: Literal["pending", "done", "blocked", "completed"] = "pending"
    result: dict | None = None
    error: str | None = None
    reason: str | None = None

@dataclass
class HITLState:
    required: bool = False
    approved: Optional[bool] = None
    comments: Optional[str] = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
