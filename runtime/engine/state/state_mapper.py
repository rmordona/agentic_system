# state/mapper.py

from dataclasses import asdict, is_dataclass
from pydantic import BaseModel
from datetime import datetime
from typing import Any

from runtime.engine.domain.agent_context import AgentContext, ArtifactSchema
from runtime.engine.domain.task import Task, HITLState

from runtime.engine.domain.envelopes import DataEnvelope, ToolEnvelope

def to_storage(obj: Any):
    if isinstance(obj, BaseModel):
        return obj.model_dump()

    if is_dataclass(obj):
        return {k: to_storage(v) for k, v in asdict(obj).items()}

    if isinstance(obj, dict):
        return {k: to_storage(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [to_storage(v) for v in obj]

    if isinstance(obj, datetime):
        return obj.isoformat()

    return obj


# -------------------------
# Rehydration Helpers
# -------------------------

def to_task(data: dict) -> Task:
    return Task(**data)


def to_hitl_state(data: dict) -> HITLState:
    return HITLState(**data)


# ================================
# AgentContext Rehydration
# ================================

def to_agent_context(data: dict) -> AgentContext:

    control = data.get("control_raw")
    if isinstance(control, dict):
        control = ArtifactSchema(**control)

    data_raw = data.get("data_raw")
    if isinstance(data_raw, dict):
        data_raw = DataEnvelope(**data_raw)

    tool_raw = data.get("tool_raw", [])
    tools: List[ToolEnvelope] = []
    for t in tool_raw:
        if isinstance(t, dict):
            tools.append(ToolEnvelope(**t))
        else:
            tools.append(t)

    return AgentContext(
        agent_name=data["agent_name"],
        stage=data["stage"],
        control_raw=control,
        data_raw=data_raw,
        tool_raw=tools,
        timestamp=data.get("timestamp"),
        result_summary=data.get("result_summary"),
    )
