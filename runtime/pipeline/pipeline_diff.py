###########################################################################
# PipelineDiff.py - Enterprise-Grade Pipeline Diff Engine
#
# Compares two pipeline versions and reports:
# - Structural changes
# - Behavioral changes
# - Governance-impacting changes
#
# Used for HITL gating, audits, and approvals.
###########################################################################


from typing import Dict, Any, List, Set

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class PipelineDiff:
    def __init__(self, old_pipeline: Dict[str, Any], new_pipeline: Dict[str, Any]):
        self.old = old_pipeline
        self.new = new_pipeline

    ###########################
    # Public API
    ###########################

    def diff(self) -> Dict[str, Any]:
        old_stages = self._stage_map(self.old)
        new_stages = self._stage_map(self.new)

        added = set(new_stages) - set(old_stages)
        removed = set(old_stages) - set(new_stages)
        common = set(old_stages) & set(new_stages)

        changed = {}
        risks: List[str] = []

        for stage in common:
            delta = self._diff_stage(old_stages[stage], new_stages[stage])
            if delta:
                changed[stage] = delta
                risks.extend(self._assess_risk(stage, delta))

        return {
            "added_stages": sorted(list(added)),
            "removed_stages": sorted(list(removed)),
            "changed_stages": changed,
            "risk_assessment": risks,
            "requires_hitl": len(risks) > 0
        }

    ###########################
    # Internal helpers
    ###########################

    def _stage_map(self, pipeline: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        return {s["name"]: s for s in pipeline.get("stages", [])}

    def _diff_stage(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        changes = {}

        if old.get("exit_condition") != new.get("exit_condition"):
            changes["exit_condition_changed"] = {
                "from": old.get("exit_condition"),
                "to": new.get("exit_condition")
            }

        old_next = self._next_stage_names(old)
        new_next = self._next_stage_names(new)

        if old_next != new_next:
            changes["next_stages_changed"] = {
                "added": sorted(list(new_next - old_next)),
                "removed": sorted(list(old_next - new_next))
            }

        if old.get("terminal") != new.get("terminal"):
            changes["terminal_changed"] = {
                "from": old.get("terminal", False),
                "to": new.get("terminal", False)
            }

        return changes

    def _next_stage_names(self, stage: Dict[str, Any]) -> Set[str]:
        return {
            n["name"] if isinstance(n, dict) else n
            for n in stage.get("next_stages", [])
        }

    ###########################
    # Risk assessment
    ###########################

    def _assess_risk(self, stage_name: str, delta: Dict[str, Any]) -> List[str]:
        risks = []

        if "exit_condition_changed" in delta:
            risks.append(
                f"Stage '{stage_name}' exit condition changed — execution behavior may differ"
            )

        if "next_stages_changed" in delta:
            added = delta["next_stages_changed"]["added"]
            removed = delta["next_stages_changed"]["removed"]

            if added:
                risks.append(
                    f"Stage '{stage_name}' introduces new routing paths: {added}"
                )
            if removed:
                risks.append(
                    f"Stage '{stage_name}' removes routing paths: {removed}"
                )

        if "terminal_changed" in delta:
            risks.append(
                f"Stage '{stage_name}' terminal status changed — pipeline completion semantics altered"
            )

        if "spec" in stage_name.lower():
            risks.append(
                f"Spec-related stage '{stage_name}' modified — requires governance review"
            )

        return risks

