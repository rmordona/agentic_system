##################################################################################
# Production-Grade Markdown Pipeline Parser (Mistune 3.x)
# ------------------------------------------------------------------------------
# Fixed: Newline preservation and robust regex property extraction.
##################################################################################

import re
import json
from pathlib import Path
from typing import List, Dict, Optional
import mistune

from runtime.pipeline.pipeline_normalizer import PipelineDSLNormalizer, PipelineNextStageParser
from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class PipelineExtractor:
    """
    Parses a governed pipeline specification written in Markdown
    into a structured JSON pipeline definition.
    """

    def __init__(self, 
        workspace_path: Path = None,
        pipeline_template_md: str = "pipeline_template.md"):

        self.pipeline_template_path = workspace_path / "templates" / pipeline_template_md
        logger.info(f"Initializing PipelineExtractor, markdown_file: {self.pipeline_template_path}")

        self.md_file = Path(self.pipeline_template_path)

        if not self.md_file.is_file():
            logger.error("Markdown file not found", extra={"path": str(self.md_file)})
            raise FileNotFoundError(f"Markdown file not found: {self.md_file}")

        self.CLOSED_STAGE_SET: List[str] = []


    def normalize_lines(self, multi_line: str) -> str:
        """
        Normalize stage lines:
        - For keys Description, Allowed Agents, Exit Condition, Next Stages:
            remove bullets, remove bold markers, standardize as 'Key: Value'
        - Keep all other lines untouched
        """
        valid_keys = {"description", "allowed agents", "exit condition", "next stages"}
        normalized_lines = []

        for line in multi_line.splitlines():
            raw_line = line  # Keep a copy in case we don't modify it
            line = line.strip()
            if not line:
                normalized_lines.append("")  # Preserve blank lines
                continue

            # Remove leading bullets and spaces
            line_no_bullet = re.sub(r"^[-*]\s*", "", line)

            # Remove bold markers around the key (**Key** -> Key)
            line_no_bold = re.sub(r"^\*\*(.*?)\*\*", r"\1", line_no_bullet)

            # Check if it's a valid key line
            if ":" in line_no_bold:
                key, value = line_no_bold.split(":", 1)
                if key.strip().lower() in valid_keys:
                    normalized_lines.append(f"{key.strip()}: {value.strip()}")
                    continue

            # Otherwise, keep the line as-is
            normalized_lines.append(raw_line)

        return "\n".join(normalized_lines)




    def parse(self) -> Dict:
        logger.info("Starting pipeline markdown parse", extra={"path": str(self.md_file)})

        md_text = self.md_file.read_text(encoding="utf-8")
        # Use mistune without a renderer to get the AST

        # Normalize text
        norm_md_text = self.normalize_lines(md_text)

        parser = mistune.create_markdown(renderer=None)
        ast = parser(norm_md_text)

        stages: List[Dict] = []
        current_stage: Optional[str] = None
        stage_lines: List[str] = []
        metadata: Dict[str, str] = {}  

        for node in ast:
            # -------- Metadata Detection (NEW) --------
            # Detects "Initial Stage: name" before any stages are defined
            if not current_stage and node["type"] == "paragraph":
                text = self._extract_inline_text(node.get("children", []))
                for line in text.split("\n"):
                    if "initial stage:" in line.lower():
                        metadata["entry_stage"] = line.split(":", 1)[1].strip()
            # -------- Headings --------
            if node["type"] == "heading":
                level = node["attrs"]["level"]
                heading_text = self._extract_inline_text(node.get("children", []))

                if level == 3 and heading_text.lower().startswith("stage:"):
                    if current_stage:
                        stages.append(self._parse_stage_content(current_stage, stage_lines))

                    current_stage = heading_text.split(":", 1)[1].strip()
                    stage_lines = []
                    continue

            # -------- Paragraphs (Key Fix: Preserving Internal Newlines) --------
            if current_stage and node["type"] == "paragraph":
                text = self._extract_inline_text(node.get("children", []))
                # Split by newline to separate properties like Description and Allowed Agents
                for line in text.split("\n"):
                    if line.strip():
                        stage_lines.append(line.strip())

            # -------- Lists --------
            if current_stage and node["type"] == "list":
                for item in node["children"]:
                    # In mistune 3, list items contain block children (usually paragraphs)
                    for child in item.get("children", []):
                        text = self._extract_inline_text(child.get("children", []))
                        # We prepend '- ' to identify this as a list item for the transition parser
                        for line in text.split("\n"):
                            if line.strip():
                                stage_lines.append(f"- {line.strip()}")

        # Final stage flush
        if current_stage:
            stages.append(self._parse_stage_content(current_stage, stage_lines))

        self.CLOSED_STAGE_SET = [s["name"] for s in stages]
        self._validate_stages(stages)

        # Ensure we return the entry_stage the linter is looking for
        return { 
            "entry_stage": metadata.get("entry_stage"),
            "stages": stages 
        }

    def _extract_inline_text(self, nodes: List[Dict]) -> str:
        """
        Extract text while explicitly preserving softbreaks and linebreaks 
        to prevent 'fusing' properties together.
        """
        parts: List[str] = []
        for node in nodes:
            if node["type"] in ("text", "codespan"):
                parts.append(node["raw"])
            elif node["type"] in ("softbreak", "linebreak"):
                parts.append("\n")
        return "".join(parts)


    def _parse_stage_content(self, stage_name: str, lines: List[str]) -> Dict:
        """
        Parses a list of cleaned strings into a Stage dictionary.
        This handles strings like '- **Description**: ...' or 'Allowed Agents: ...'
        """
        description = ""
        allowed_agents = []
        exit_condition = None
        terminal = False
        next_stages = []
        is_next_stages = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 1. Detect transition to Next Stages block
            # This triggers if we see "Next Stages:" or if we are already in the list
            if "next stages" in line_str.lower() and ":" in line_str:
                is_next_stages = True
                # If there's content after "Next Stages:", check if it's a transition
                potential_val = line_str.split(":", 1)[1].strip()
                if not potential_val:
                    continue
                line_str = potential_val # Fall through to transition parsing

            # 2. Handle Key-Value parsing (Description, Agents, Exit Condition)
            if not is_next_stages and ":" in line_str:
                # Remove Markdown noise: lstrip bullets and remove bolding
                clean_line = line_str.lstrip("- ").replace("**", "").strip()
                
                parts = clean_line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    val = parts[1].strip()

                    if key == "description":
                        description = val
                        continue
                    elif key == "allowed agents":
                        raw = val.strip("[]").replace("'", "").replace('"', "")
                        allowed_agents = [a.strip() for a in raw.split(",") if a.strip()]
                        continue
                    elif key == "exit condition":
                        exit_condition = val
                        continue
                    elif key == "terminal":
                        terminal = val.lower() == "true"
                        continue

            # 3. Handle Transitions (Next Stages list)
            # We assume transitions start with a bullet or follow the Next Stages header
            if is_next_stages or line_str.startswith("-"):
                # Clean the line of "Next Stages:" prefix if it exists on same line
                clean_transition = line_str.replace("Next Stages:", "").strip()
                if clean_transition:
                    # Use your existing normalizer and parser
                    normalized = PipelineDSLNormalizer.normalize_pipeline_text(clean_transition)
                    parsed = PipelineNextStageParser.parse(normalized)
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


    def _validate_stages(self, stages: List[Dict]) -> None:
        """Ensures integrity and reachability of the parsed pipeline."""
        seen = set()
        for stage in stages:
            name = stage["name"]
            if name in seen:
                raise ValueError(f"Duplicate stage: {name}")
            seen.add(name)

            if stage["terminal"]:
                if stage["next_stages"]:
                    raise ValueError(f"Terminal stage '{name}' cannot have next_stages")
            else:
                for ns in stage["next_stages"]:
                    if ns["name"] not in self.CLOSED_STAGE_SET:
                        raise ValueError(f"Stage '{name}' references unknown stage '{ns['name']}'")