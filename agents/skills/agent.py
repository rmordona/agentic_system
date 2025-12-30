from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from agents.skills.base_skill import BaseSkill


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
        llm,
        memory_manager,
        embedding_store,
        tool_client,
        event_bus=None
    ):
        self.workspace_path = workspace_path
        self.stage_meta = stage_meta
        self.skill_name = skill_name

        skill_dir = workspace_path / "skills" / skill_name
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill not found: {skill_dir}")

        super().__init__(
            skill_dir=skill_dir,
            llm=llm,
            memory_manager=memory_manager,
            embedding_store=embedding_store,
            tool_client=tool_client,
            event_bus=event_bus
        )

        # From skill.json
        self.role = self.skill_meta["role"]
        self.exit_condition = self.skill_meta.get("exit_condition")

    # ------------------------------------------------------------------
    # LangGraph Node Entry Point
    # ------------------------------------------------------------------

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph async node entry.
        """

        # ---- Stage gate
        if not self._allowed_in_stage(state):
            return {}

        # ---- Agent exit condition
        if self._should_exit(state):
            return {}

        # ---- Delegate to BaseSkill
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
        """
        Agent-level exit logic, defined in skill.json
        """
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
