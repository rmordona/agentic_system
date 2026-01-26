# -----------------------------------------------------------------------------
# Project: Agentic System
# File: agents/impersonator/agent.py
#
# Description:
#
#    ImpersonatorAgent is a LangGraph node wrapper around BaseSkill.
#
#    It enforces stage constraints and agent-level exit conditions while
#    delegating execution, memory usage, and tool invocation to BaseSkill.
#
#    ImpersonatorAgent does NOT implement business logic or prompting —
#    it exists to integrate skills into the execution graph.
#   
# -----------------------
# AGENT.md vs SKILL.md — The Non-Negotiable Conceptual Split
#
#
# AGENT.md
#   “What am I responsible for deciding, and under what authority and constraints?”
#
# SKILL.md
#   “If authorized, how do I perform a specific operation?”
#
# Decision rule:
#   If you answer **why / whether / should** → AGENT.md
#   If you answer **how / steps / method** → SKILL.md
#
#
# AGENT.md - defines INTENT, AUTHORITY, and JUDGMENT POSTURE.
#          - it describes the agent to impersonate
#
# It answers:
#   “If I were this role, what decisions am I responsible for,
#    and under what constraints?”
#
# AGENT.md specifies:
#   - Goals and non-goals
#   - Safety and governance constraints
#   - What kinds of outputs are acceptable
#   - What constitutes success or failure
#   - What the agent must explicitly refuse to do
#
# AGENT.md does NOT define how actions are performed.
#
# ---------------------- 
#
# SKILL.md defines CAPABILITY, METHOD, and PROCEDURE.
#
# It answers:
#   “Given permission, how do I perform a specific operation?”
#
# SKILL.md specifies:
#   - Techniques
#   - Step-by-step procedures
#   - Algorithms
#   - Tools and execution methods
#   - Heuristics and reusable logic
#
# A skill is agnostic to intent and authority.
#
# -------------------
#
# Important clarification:
#   SKILL.md is NOT limited to frequently repeated tasks.
#
# Correct principle:
#   SKILL.md is for reusable capabilities — not usage frequency.
#
# A skill may be:
#   - Used once
#   - Used rarely
#   - Used in a single pipeline
#
# What matters is orthogonality, not repetition.
#
# If a capability:
#   - Can logically be reused
#   - Can be tested independently
#   - Can be swapped, versioned, or replaced
#
# Then it belongs in SKILL.md.
#
# ---------
#
# ------------------------------------------------------------------------------
# Capability Leakage Risk & Mandatory Skill Scoping
# ------------------------------------------------------------------------------
# Unscoped global skill registries introduce a critical failure mode in agentic
# systems: capability leakage.
#
# The risk is real and well-documented. Allowing an LLM or executor to freely
# select from a global pool of skills can result in:
#
# - Authority escalation beyond the agent’s mandate
# - Goal drift away from declared intent
# - Unintended or unsafe tool usage
# - Audit and traceability failures (“why did it do that?”)
# - Silent safety and governance violations
#
# This is not a modeling issue; it is a system design flaw.
#
# Non-Negotiable Principle:
# Skills must be reachable only through explicitly authorized agents.
#
# Forbidden:
#   Executor → Any SKILL.md
#
# Required:
#   Executor → AGENT.md → Attached SKILL.md
#
# This constraint preserves intent-capability alignment, enforces least
# privilege, and ensures deterministic, auditable execution.
# -------------------------------
#
#
# Author: Raymond M.O. Ordona
# Created: 2025-12-31
# Copyright:
#   © 2025 Raymondn Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from runtime.agent.base_agent import BaseAgent
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient
from events.event_bus import EventBus

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

class ImpersonatorAgent(BaseAgent):
    """
    ImpersonatorAgent is a LangGraph node that extends BaseSkill with:
    - stage constraints
    - agent-level exit conditions
    """

    def __init__(
        self,
        workspace_path: Path,
        agent_name: str,
        stage_meta: dict,
        runtime_context,    
        model_manager: ModelManager,
        tool_client: ToolClient,  
        event_bus: EventBus = None
    ):
        #self.workspace_path = workspace_path
        #self.stage_meta = stage_meta
        #self.skill_name = skill_name

        # 🔑 Delegate filesystem responsibility to BaseSkill
        super().__init__(
            workspace_dir=workspace_path,
            agent_name=agent_name,
            runtime_context=runtime_context,  # pass context to BaseSkill as memory_manager
            model_manager=model_manager,
            tool_client=tool_client,
            event_bus=event_bus
        )

        # From skill.json (already loaded by BaseSkill)
        self.role = self.skill_meta["role"]
        self.exit_condition = self.skill_meta.get("exit_condition")

    # ------------------------------------------------------------------
    # LangGraph Node Entry Point
    # ------------------------------------------------------------------

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(f"Entering next agent run (__call__): {state}")

        if not self._allowed_in_stage(state):
            return {}

        if self._should_exit(state):
            return {}

        return await self.run(state)

    # ------------------------------------------------------------------
    # Stage Constraints
    # ------------------------------------------------------------------

    def _allowed_in_stage(self, state: dict) -> bool:
        stage_name = state["stage"]

        stage_cfg = self.stage_meta.get(stage_name)
        if not stage_cfg:
            return True

        allowed = stage_cfg.get("allowed_agents")
        if not allowed:
            return True

        return self.role in allowed

    # ------------------------------------------------------------------
    # Agent Exit Conditions (skill.json)
    # ------------------------------------------------------------------

    def _should_exit(self, state: dict) -> bool:
        if not self.exit_condition:
            return False

        condition_type = self.exit_condition.get("type")
        executed = state.get("executed_agents_per_stage", {})
        stage_exec = executed.get(state["stage"], [])

        if condition_type == "once_per_stage":
            return self.role in stage_exec

        if condition_type == "max_runs":
            max_runs = self.exit_condition.get("max", 1)
            return stage_exec.count(self.role) >= max_runs

        if condition_type == "until_field_set":
            field = self.exit_condition.get("field")
            return bool(state.get(field))

        return False
