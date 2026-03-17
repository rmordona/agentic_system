# runtime/engine/governance/policy_context_resolver.py

from __future__ import annotations
from typing import Dict, Any
from runtime.logger import AgentLogger
from runtime.engine.stage.stage_schema import StageSchema

logger = AgentLogger.get_logger(component="system")


class PolicyContextResolver:
    """
    Resolves all available symbols for policy evaluation.

    Responsibilities:
    - Merge artifact, stage inputs, HITL flags, and agent outputs
    - Prepend `ctx.` style variables for PolicyRegistry normalization
    - Ensure missing keys are set to None to avoid runtime errors
    """

    def __init__(self, stage: StageSchema, artifact: Dict[str, Any], agent_outputs: Dict[str, Any], hitl_flags: Dict[str, Any]):
        self.stage = stage
        self.artifact = artifact
        self.agent_outputs = agent_outputs
        self.hitl_flags = hitl_flags

    def resolve_symbols(self) -> Dict[str, Any]:
        """
        Flatten everything into a single dictionary for PolicyRegistry.
        """

        symbols: Dict[str, Any] = {}

        # Stage-specific context inputs
        for key in getattr(self.stage, "context_inputs", []):
            symbols[key] = self.artifact.get(key) or self.agent_outputs.get(key) or None

        # Add all artifact keys
        symbols.update(self.artifact)

        # Add agent outputs (latest)
        symbols.update(self.agent_outputs)

        # Add HITL flags
        symbols.update(self.hitl_flags)

        # Ensure known stage metadata variables are included
        symbols["stage_name"] = getattr(self.stage, "name", None)

        logger.info(f"Resolved policy symbols: {list(symbols.keys())}")

        return symbols
