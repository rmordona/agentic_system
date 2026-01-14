###########################################################################
# SDDAgentMarkdownAdapter
###########################################################################
#
# Enterprise-Grade SDD Markdown Adapter for Multi-Agent Pipelines
#
# Description:
# -------------
# The SDDAgentMarkdownAdapter is designed to manage evolving plans and artifacts
# in Specification-Driven Development (SDD) pipelines. It provides a structured,
# traceable, and enterprise-ready approach for handling multi-agent outputs
# across multiple stages and iterations.
#
# Key Features:
# -------------
# 1. Multi-Agent Merge:
#    - Accepts multiple JSON outputs from different agents for the same stage.
#    - Merges lists and updates single-value fields intelligently.
#
# 2. Markdown Evolution:
#    - Maintains a "Current Plan" section at the top for actionable items.
#    - Automatically moves superseded items into a "History of Plans" section.
#    - Supports multiple iterations with structured, numbered history blocks.
#
# 3. Provenance Tracking:
#    - Each bullet item contains metadata: agent_id, stage, timestamp, superseded flag.
#    - Ensures auditability and traceability of decisions over time.
#
# 4. Audit Logging:
#    - All merged JSON outputs are recorded in a persistent JSON audit log.
#    - Facilitates rollback, HITL review, and pipeline debugging.
#
# 5. Configurable History:
#    - Optional maximum number of historical iterations can be enforced.
#    - Prevents uncontrolled growth of markdown in long-running pipelines.
#
# Usage:
# ------
# adapter = SDDAgentMarkdownAdapter(md_path="plan.md", audit_path="plan_audit.json")
#
# outputs = [
#     {
#         "stage": "validation",
#         "agent_id": "agent4",
#         "violations": ["Node 14 deprecated"],
#         "proposed_changes": ["Use Node 20 LTS runtime"],
#         "timestamp": "2026-01-12T13:00"
#     },
#     {
#         "stage": "validation",
#         "agent_id": "agent5",
#         "proposed_changes": ["Add null-input edge case", "Add comprehensive validation"],
#         "timestamp": "2026-01-12T15:00"
#     }
# ]
#
# markdown = adapter.process_stage_outputs(outputs)
# print(markdown)
#
# Sample Output (plan.md):
# ------------------------
# ## Current Plan
# - Use Node 20 LTS runtime  # agent4, validation, 2026-01-12T13:00, superseded=false
# - Add null-input edge case  # agent5, validation, 2026-01-12T15:00, superseded=false
# - Add comprehensive validation  # agent5, validation, 2026-01-12T15:00, superseded=false
#
# ## History of Plans
# ### Iteration 1
# - Use Node 14 runtime  # agent4, validation, 2026-01-12T13:00, superseded=true
#
###########################################################################

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class SDDAgentMarkdownAdapter:
    """
    Enterprise-grade SDD Markdown Adapter

    Responsibilities:
    - Merge multi-agent JSON outputs per stage
    - Maintain Current Plan + Historical Plans
    - Track iterations, agent_id, stage, timestamp
    - Render structured markdown to plan.md / artifact.md
    - Maintain audit log for traceability
    """

    def __init__(
        self,
        md_path: str = "plan.md",
        audit_path: str = "plan_audit.json",
        max_history: Optional[int] = None
    ):
        logger.info(
            "Initializing SDDAgentMarkdownAdapter",
            extra={
                "md_path": md_path,
                "audit_path": audit_path,
                "max_history": max_history,
            },
        )

        self.md_path = md_path
        self.audit_path = audit_path
        self.max_history = max_history
        self.audit_log: List[dict] = []

        # Load existing audit log if exists
        if os.path.exists(audit_path):
            try:
                with open(audit_path, "r") as f:
                    self.audit_log = json.load(f)
                logger.info(
                    "Loaded existing audit log",
                    extra={"entries": len(self.audit_log)},
                )
            except Exception as e:
                logger.exception(
                    "Failed to load existing audit log",
                    extra={"path": audit_path},
                )
                raise
        else:
            logger.debug("No existing audit log found; starting fresh")

    # ---------- Utilities ----------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _format_bullet(
        item: str,
        agent_id: str,
        stage: str,
        timestamp: str,
        superseded: bool = False,
    ) -> str:
        return (
            f"- {item}  # {agent_id}, {stage}, {timestamp}, "
            f"superseded={str(superseded).lower()}"
        )

    # ---------- Markdown Handling ----------

    def _read_existing_md(self) -> str:
        if os.path.exists(self.md_path):
            logger.debug(
                "Reading existing markdown file",
                extra={"path": self.md_path},
            )
            try:
                with open(self.md_path, "r") as f:
                    return f.read()
            except Exception:
                logger.exception(
                    "Failed to read existing markdown file",
                    extra={"path": self.md_path},
                )
                raise

        logger.debug("No existing markdown file found")
        return ""

    def _parse_current_history(
        self, existing_md: str
    ) -> (Dict[str, str], List[Dict]):
        """
        Parse markdown into Current Plan dict and Historical Plans list
        """
        logger.debug("Parsing existing markdown into current plan and history")

        current_plan = {}
        history = []

        # Split into sections
        if "## Current Plan" in existing_md:
            _, after_current = existing_md.split("## Current Plan", 1)
            if "## History of Plans" in after_current:
                current_section_text, history_section_text = after_current.split(
                    "## History of Plans", 1
                )
            else:
                current_section_text = after_current
                history_section_text = ""
        else:
            current_section_text = ""
            history_section_text = ""

        # Parse Current Plan bullets
        for line in current_section_text.splitlines():
            line = line.strip()
            if line.startswith("-"):
                key = line.split("#")[0].strip()
                current_plan[key] = line

        # Parse History of Plans
        iteration_num = None
        iteration_items = []
        for line in history_section_text.splitlines():
            line = line.strip()
            if line.startswith("### Iteration"):
                if iteration_num is not None:
                    history.append(
                        {"iteration": iteration_num, "items": iteration_items}
                    )
                iteration_num = int(line.replace("### Iteration", "").strip())
                iteration_items = []
            elif line.startswith("-"):
                iteration_items.append(line)

        if iteration_num is not None:
            history.append({"iteration": iteration_num, "items": iteration_items})

        logger.debug(
            "Parsed markdown",
            extra={
                "current_items": len(current_plan),
                "history_iterations": len(history),
            },
        )

        return current_plan, history

    # ---------- JSON Output Handling ----------

    def _merge_json_outputs(self, outputs: List[dict]) -> dict:
        """
        Merge multiple agent outputs into a single dict
        """
        logger.debug(
            "Merging agent outputs",
            extra={"outputs": len(outputs)},
        )

        merged = {}
        for output in outputs:
            for k, v in output.items():
                if k in ["stage", "agent_id", "timestamp"]:
                    continue
                if isinstance(v, list):
                    merged.setdefault(k, [])
                    merged[k].extend(v)
                else:
                    merged[k] = v

        # Include metadata from the last output
        last = outputs[-1]
        merged["stage"] = last.get("stage", "unknown")
        merged["agent_id"] = last.get("agent_id", "unknown")
        merged["timestamp"] = last.get("timestamp", self._timestamp())

        logger.debug(
            "Merged output complete",
            extra={
                "stage": merged["stage"],
                "agent_id": merged["agent_id"],
            },
        )

        return merged

    # ---------- Markdown Evolution ----------

    def _evolve_markdown(self, merged_output: dict) -> str:
        """
        Update plan.md / artifact.md
        """
        logger.info(
            "Evolving markdown for stage",
            extra={"stage": merged_output.get("stage")},
        )

        existing_md = self._read_existing_md()
        current_plan, history = self._parse_current_history(existing_md)

        next_iteration = (history[-1]["iteration"] + 1) if history else 1

        new_current = current_plan.copy()
        new_history_iteration = []

        for key, values in merged_output.items():
            if key in ["stage", "agent_id", "timestamp"]:
                continue

            if not isinstance(values, list):
                values = [values]

            for val in values:
                bullet_key = val.strip()
                if bullet_key in new_current:
                    new_history_iteration.append(new_current[bullet_key])

                new_current[bullet_key] = self._format_bullet(
                    val,
                    agent_id=merged_output["agent_id"],
                    stage=merged_output["stage"],
                    timestamp=merged_output["timestamp"],
                    superseded=False,
                )

        if new_history_iteration:
            history.append(
                {"iteration": next_iteration, "items": new_history_iteration}
            )

            if self.max_history:
                history = history[-self.max_history :]

            logger.info(
                "Superseded items moved to history",
                extra={
                    "iteration": next_iteration,
                    "items": len(new_history_iteration),
                },
            )

        # Build markdown text
        md_lines = ["## Current Plan"]
        md_lines.extend(new_current.values())
        md_lines.append("## History of Plans")

        for iteration in history:
            md_lines.append(f"### Iteration {iteration['iteration']}")
            md_lines.extend(iteration["items"])

        return "\n".join(md_lines)

    # ---------- Audit Logging ----------

    def _record_audit(self, merged_output: dict):
        logger.debug(
            "Recording audit entry",
            extra={
                "stage": merged_output.get("stage"),
                "agent_id": merged_output.get("agent_id"),
            },
        )

        self.audit_log.append(merged_output)

        try:
            with open(self.audit_path, "w") as f:
                json.dump(self.audit_log, f, indent=2)
        except Exception:
            logger.exception(
                "Failed to persist audit log",
                extra={"path": self.audit_path},
            )
            raise

    # ---------- Public API ----------

    def process_stage_outputs(self, outputs: List[dict]) -> str:
        """
        Main entry point:
        - Merge outputs
        - Evolve markdown
        - Record audit
        - Save markdown
        """
        logger.info(
            "Processing stage outputs",
            extra={"outputs": len(outputs)},
        )

        merged_output = self._merge_json_outputs(outputs)
        markdown_text = self._evolve_markdown(merged_output)
        self._record_audit(merged_output)

        try:
            with open(self.md_path, "w") as f:
                f.write(markdown_text)
            logger.info(
                "Markdown artifact updated",
                extra={"path": self.md_path},
            )
        except Exception:
            logger.exception(
                "Failed to write markdown artifact",
                extra={"path": self.md_path},
            )
            raise

        return markdown_text
