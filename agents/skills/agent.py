# -----------------------------------------------------------------------------
# Project: Agentic System
# File: agents/skills/agent.py
#
# Description:
#
#    SkillAgent is a LangGraph node wrapper around BaseSkill.
#
#    It enforces stage constraints and agent-level exit conditions while
#    delegating execution, memory usage, and tool invocation to BaseSkill.
#
#    SkillAgent does NOT implement business logic or prompting —
#    it exists to integrate skills into the execution graph.
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

from agents.skills.base_skill import BaseSkill
from llm.model_manager import ModelManager
from runtime.tools.client import ToolClient
from events.event_bus import EventBus

class SkillAgent(BaseSkill):
    """
    SkillAgent is a LangGraph node that extends BaseSkill with:
    - stage constraints
    - agent-level exit conditions
    """

    def __init__(
        self,
        workspace_path: Path,
        skill_name: str,
        stage_meta: dict,
        runtime_context,        
        model_manager: ModelManager,
        tool_client: ToolClient,
        event_bus: EventBus = None
    ):
        self.workspace_path = workspace_path
        self.stage_meta = stage_meta
        self.skill_name = skill_name

        # 🔑 Delegate filesystem responsibility to BaseSkill
        super().__init__(
            workspace_dir=workspace_path,
            skill_name=skill_name,
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
