#!/usr/bin/env python3
"""
Production-Grade Markdown Pipeline Parser (Mistune 3.x)
------------------------------------------------------
- Converts Spec-Driven Development pipeline templates into structured JSON
- Deterministic, auditable, and reproducible
- No LLM dependency
- Designed for agentic orchestration frameworks
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import mistune


class MarkdownPipelineParser:
    """
    Parses a governed pipeline specification written in Markdown
    into a structured JSON pipeline definition.
    """

    # -------------------------
    # Lifecycle
    # -------------------------
    def __init__(self, md_file: str):
        self.md_file = Path(md_file)
        if not self.md_file.is_file():
            raise FileNotFoundError(f"Markdown file not found: {md_file}")

        self.CLOSED_STAGE_SET: List[str] = []

    # -------------------------
    # Public API
    # -------------------------
    def parse(self) -> Dict:
        """
        Parse markdown pipeline template into structured JSON.
        """
        md_text = self.md_file.read_text(encoding="utf-8")
        parser = mistune.create_markdown(renderer=None)
        ast = parser(md_text)

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
                    block = item["children"][0]  # block_text
                    text = self._extract_inline_text(
                        block.get("children", [])
                    )
                    stage_lines.append(f"- {text}")

        # Final stage flush
        if current_stage:
            stages.append(
                self._parse_stage_content(current_stage, stage_lines)
            )

        self.CLOSED_STAGE_SET = [s["name"] for s in stages]

        print(self.CLOSED_STAGE_SET)
        self._validate_stages(stages)

        return {"stages": stages}

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

    def _parse_stage_content(
        self, stage_name: str, lines: List[str]
    ) -> Dict:
        """
        Parse a single stage block into structured fields.
        """
        description: str = ""
        allowed_agents: List[str] = []
        exit_condition: Optional[str] = None
        terminal: bool = False
        next_stages: List[Dict[str, Optional[str]]] = []

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
                if "— if " in body:
                    name, cond = body.split("— if ", 1)
                    next_stages.append(
                        {"name": name.strip(), "condition": cond.strip()}
                    )
                else:
                    next_stages.append(
                        {"name": body.strip(), "condition": None}
                    )

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
        seen = set()

        for stage in stages:
            name = stage["name"]

            if name in seen:
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
                    raise ValueError(
                        f"Stage '{name}' missing field '{field}'"
                    )

            # Terminal rules
            if stage["terminal"]:
                if stage["next_stages"]:
                    raise ValueError(
                        f"Terminal stage '{name}' must have no next_stages"
                    )
                if stage["exit_condition"] is not None:
                    raise ValueError(
                        f"Terminal stage '{name}' must not have exit_condition"
                    )

            # Next stage validation
            for ns in stage["next_stages"]:
                if ns["name"] not in self.CLOSED_STAGE_SET:
                    raise ValueError(
                        f"Stage '{name}' references unknown stage '{ns['name']}'"
                    )
                if ns["condition"] in self.CLOSED_STAGE_SET:
                    raise ValueError(
                        f"Stage '{name}' condition invalid: {ns['condition']}"
                    )


# -------------------------
# Standalone entrypoint
# -------------------------
if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser(
        description="Parse pipeline markdown into JSON"
    )
    cli.add_argument("md_file", help="Pipeline markdown file")
    args = cli.parse_args()

    parser = MarkdownPipelineParser(args.md_file)
    pipeline = parser.parse()
    print(json.dumps(pipeline, indent=2))
