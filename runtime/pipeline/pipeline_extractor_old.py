##################################################################################
# Production-Grade Markdown Pipeline Parser (Mistune 3.x)
# ------------------------------------------------------------------------------
# Purpose:
#   Deterministically converts Spec-Driven Development (SDD) pipeline definitions
#   written in Markdown into a structured, machine-verifiable JSON format.
#
# Design Guarantees:
#   - Deterministic execution (no LLM involvement)
#   - Fully auditable and reproducible
#   - Static, schema-driven extraction
#   - Designed for agentic orchestration frameworks
#
# Operational Characteristics:
#   - Safe for CI/CD validation gates
#   - Safe for runtime admission control
#   - Emits structured logs for observability
#
# Dependencies:
#   - mistune 3.x (AST-based Markdown parsing)
#
# Non-Goals:
#   - No inference
#   - No heuristic interpretation
#   - No runtime execution semantics
##################################################################################

import re
import json
from pathlib import Path
from typing import List, Dict, Optional
import mistune
import unicodedata

from runtime.pipeline.pipeline_normalizer import PipelineDSLNormalizer, PipelineNextStageParser
from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class PipelineExtractor:
    """
    Parses a governed pipeline specification written in Markdown
    into a structured JSON pipeline definition.

    This class is intentionally deterministic and side-effect free,
    aside from structured logging.
    """

    # -------------------------
    # Lifecycle
    # -------------------------
    def __init__(self, 
        workspace_path: str = None,
        pipeline_template_md: str = "pipeline_template.md"):

        self.pipeline_template_path = workspace_path / "templates" / pipeline_template_md
        logger.info( f"Initializing PipelineExtractor, markdown_file: {self.pipeline_template_path}")

        self.md_file = Path(self.pipeline_template_path)

        if not self.md_file.is_file():
            logger.error(
                "Markdown file not found",
                extra={"path": md_file},
            )
            raise FileNotFoundError(f"Markdown file not found: {md_file}")

        self.CLOSED_STAGE_SET: List[str] = []

    # -------------------------
    # Public API
    # -------------------------
    def parse(self) -> Dict:
        """
        Parse markdown pipeline template into structured JSON.
        """
        logger.info(
            "Starting pipeline markdown parse",
            extra={"path": str(self.md_file)},
        )

        md_text = self.md_file.read_text(encoding="utf-8")
        parser = mistune.create_markdown(renderer=None)
        ast = parser(md_text)

        logger.debug(
            "Markdown parsed into AST",
            extra={"node_count": len(ast)},
        )

        stages: List[Dict] = []
        current_stage: Optional[str] = None
        stage_lines: List[str] = []

        for node in ast:
            # -------- Headings --------
            if node["type"] == "heading":
                level = node["attrs"]["level"]
                heading_text = self._extract_inline_text(
                    node.get("children", [])
                )

                if level == 3 and heading_text.lower().startswith("stage:"):
                    logger.debug(f"Stage heading detected, stage: {heading_text}")

                    if current_stage:
                        stages.append(
                            self._parse_stage_content(
                                current_stage, stage_lines
                            )
                        )

                    current_stage = heading_text.split(":", 1)[1].strip()
                    stage_lines = []
                    continue

            # -------- Paragraphs --------
            if current_stage and node["type"] == "paragraph":
                text = self._extract_inline_text(
                    node.get("children", [])
                )
                for line in text.splitlines():
                    if line.strip():
                        stage_lines.append(line.strip())

            # -------- Lists --------
            if current_stage and node["type"] == "list":
                for item in node["children"]:
                    block = item["children"][0]
                    text = self._extract_inline_text(
                        block.get("children", [])
                    )
                    stage_lines.append(f"- {text}")

        # Final stage flush
        if current_stage:
            stages.append(
                self._parse_stage_content(current_stage, stage_lines)
            )

        logger.info(f"Stage blocks parsed,stage_count: {len(stages)}")

        self.CLOSED_STAGE_SET = [s["name"] for s in stages]

        logger.info(f"Set: {self.CLOSED_STAGE_SET}")

        logger.debug(f"Closed stage set finalized, stages: {self.CLOSED_STAGE_SET}")

        self._validate_stages(stages)

        logger.info(f"Pipeline markdown parsing completed successfully, stage_count: {len(stages)}")

        return { "stages" : stages }

    # -------------------------
    # Internal helpers
    # -------------------------
    def _extract_inline_text(self, nodes: List[Dict]) -> str:
        """
        Extract plain text from mixed inline AST nodes.
        """
        parts: List[str] = []
        for node in nodes:
            if node["type"] in ("text", "codespan"):
                parts.append(node["raw"])
            elif node["type"] == "linebreak":
                parts.append("\n")
        return "".join(parts).strip()

    def _parse_stage_content(self, stage_name: str, lines: List[str]) -> Dict:
        description = ""
        allowed_agents = []
        exit_condition = None
        terminal = False
        next_stages = []
        is_next_stages = False

        # Regex to capture the key and value regardless of bullet points or bolding
        # Matches: "- **Description**: value", "Description: value", etc.
        key_val_pattern = re.compile(r"^(?:\s*-\s*)?(?:\*\*)?([a-zA-Z\s]+)(?:\*\*)?:\s*(.*)$")

        for line in lines:
            match = key_val_pattern.match(line)
            
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()

                if key == "description":
                    description = value
                elif key == "allowed agents":
                    raw = value.strip("[]")
                    allowed_agents = [a.strip().strip('"').strip("'") for a in raw.split(",") if a.strip()]
                elif key == "exit condition":
                    exit_condition = value
                elif key == "terminal":
                    terminal = value.lower() == "true"
                elif key == "next stages":
                    is_next_stages = True
                    continue # The header itself isn't a stage

            # Handle the transition list items
            if is_next_stages and line.strip().startswith("-"):
                normalized_line = PipelineDSLNormalizer.normalize_pipeline_text(line)
                parsed = PipelineNextStageParser.parse(normalized_line)
                if parsed:
                    next_stages.append(parsed)

        return {
            "name": stage_name,
            "description": description,
            "allowed_agents": allowed_agents,
            "exit_condition": exit_condition,
            "next_stages": next_stages,
            "terminal": terminal,
        }
 
    def _parse_stage_content1(
        self, stage_name: str, lines: List[str]
    ) -> Dict:
        """
        Parse a single stage block into structured fields.
        """
        logger.debug(f"Parsing stage content, stage: {stage_name}, line_count: {len(lines)}")

        description: str = ""
        allowed_agents: List[str] = []
        exit_condition: Optional[str] = None
        terminal: bool = False
        next_stages: List[Dict[str, Optional[str]]] = []
        is_next_stages: bool = False

        for line in lines:

            lower = line.lower()

            if lower.startswith("description:"):
                description = line.split(":", 1)[1].strip()

            elif lower.startswith("allowed agents:"):
                raw = line.split(":", 1)[1].strip().strip("[]")
                allowed_agents = [
                    a.strip().strip('"').strip("'")
                    for a in raw.split(",")
                    if a.strip()
                ]

            elif lower.startswith("exit condition:"):
                exit_condition = line.split(":", 1)[1].strip()

            elif lower.startswith("terminal:"):
                terminal = (
                    line.split(":", 1)[1].strip().lower() == "true"
                )

            elif line.startswith("-"):
                body = line[1:].strip()

                if is_next_stages:
                    normalized_line = PipelineDSLNormalizer.normalize_pipeline_text(line)

                    parsed = PipelineNextStageParser.parse(normalized_line)
                    if not parsed:
                        raise SyntaxError(
                            f"Invalid Next Stage syntax: '{parsed}'"
                        )
                    next_stages.append(parsed)

            elif line.startswith("Next Stages:"):
                    is_next_stages = True
            else:
                logger.info(f"Unknown line: {line}")

        return {
            "name": stage_name,
            "description": description,
            "allowed_agents": allowed_agents,
            "exit_condition": exit_condition,
            "next_stages": next_stages,
            "terminal": terminal,
        }

    # -------------------------
    # Validation
    # -------------------------
    def _validate_stages(self, stages: List[Dict]) -> None:
        """
        Validate pipeline correctness and safety.
        """
        logger.info(
            "Validating parsed pipeline stages",
            extra={"stage_count": len(stages)},
        )

        seen = set()

        for stage in stages:
            name = stage["name"]

            if name in seen:
                logger.error(f"Duplicate stage detected, stage: {name}")
                raise ValueError(f"Duplicate stage: {name}")
            seen.add(name)

            # Required fields
            for field in (
                "description",
                "allowed_agents",
                "exit_condition",
                "next_stages",
                "terminal",
            ):
                if field not in stage:
                    logger.error(f"Stage missing required field, stage: {name}, field: {field}")
                    raise ValueError( f"Stage '{name}' missing field '{field}'")

            # Terminal rules
            if stage["terminal"]:
                if stage["next_stages"]:
                    logger.error(f"Terminal stage defines next_stages, stage: {name}")
                    raise ValueError(
                        f"Terminal stage '{name}' must have no next_stages"
                    )
                if stage["exit_condition"] is not None:
                    logger.error(f"Terminal stage defines exit_condition, stage: {name}")
                    raise ValueError(
                        f"Terminal stage '{name}' must not have exit_condition"
                    )

            # Next stage validation
            for ns in stage["next_stages"]:
                if ns["name"] not in self.CLOSED_STAGE_SET:
                    logger.error(f"Unknown next stage referenced, stage: {name}, next_stage: {ns["name"]}")

                    raise ValueError(
                        f"Stage '{name}' references unknown stage '{ns['name']}'"
                    )
                if ns["condition"] in self.CLOSED_STAGE_SET:
                    logger.error(f"Invalid next stage condition, stage: {name}, condition: {ns["condition"]}")

                    raise ValueError(
                        f"Stage '{name}' condition invalid: {ns['condition']}"
                    )

        logger.info("Pipeline validation completed successfully")

