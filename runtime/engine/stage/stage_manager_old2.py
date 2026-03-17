from __future__ import annotations

import re
import mistune
from pathlib import Path
from typing import Dict, List, Tuple, Any

from core.paths import WORKSPACES_ROOT
from runtime.logger import AgentLogger
from runtime.engine.stage.stage_schema import StageSchema
from runtime.engine.stage.stage_registry import StageRegistry
from runtime.engine.policy.policy_registry import PolicyRegistry

logger = AgentLogger.get_logger(component="system")


class StageManager:
    """
    Governance Execution Policy controller.

    Converts governance_policy.md into a deterministic stage machine.
    """

    TRANSITION_PATTERN = re.compile(
        r"IF\s+`?(?P<condition>.*?)`?\s+ALLOW\s+`?(?P<target>[a-zA-Z0-9_]+)`?",
        re.IGNORECASE,
    )

    ALWAYS_PATTERN = re.compile(
        r"ALWAYS\s+ALLOW\s+`?(?P<target>[a-zA-Z0-9_]+)`?",
        re.IGNORECASE,
    )

    def __init__(self, workspace_name: str):

        self.workspace_path = WORKSPACES_ROOT / workspace_name
        self.policy_path = self.workspace_path / "templates" / "governance_policy.md"

        self.registry = StageRegistry()
        self.policy_registry = PolicyRegistry(workspace_name)

        self.md_parser = mistune.create_markdown(renderer="ast")

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def register_stages(self):

        if not self.policy_path.exists():
            raise FileNotFoundError(f"GEP not found: {self.policy_path}")

        raw = self.policy_path.read_text()
        tokens = self.md_parser(raw)

        stage_blocks = self._group_tokens_by_stage(tokens)

        for idx, (stage_name, block) in enumerate(stage_blocks.items()):


            # Construct StageSchema with dataclass
            schema = StageSchema(
                name=stage_name,
                description=block.get("description", f"Stage {stage_name}"),
                allowed_agents=block.get("agents", []),
                terminal=self._is_terminal_stage(stage_name, block),
                priority=block.get("priority", 1),
            )

            entry_preds = [
                self.policy_registry.compile(expr)
                for expr in block["entry_predicates"]
            ]

            exit_preds = [
                self.policy_registry.compile(expr)
                for expr in block["exit_predicates"]
            ]

            transitions = self._parse_transitions(block["logic"])

            self.registry.register_stage(
                stage=schema,
                entry_conditions=entry_preds,
                exit_conditions=exit_preds,
                transitions=transitions,
                entry=(idx == 0),
            )

        logger.info(
            f"GEP Loaded successfully: {len(self.registry.list_stages())} stages"
        )

    # ---------------------------------------------------------
    # Markdown Parsing
    # ---------------------------------------------------------

    def _group_tokens_by_stage(self, tokens) -> Dict[str, Dict]:

        stages = {}
        current_stage = None

        for token in tokens:

            if token.get("type") == "heading":

                text = self._extract_text(token)

                if "Stage:" in text:
                    stage_name = text.split("Stage:")[1].strip()

                    current_stage = stage_name

                    stages[current_stage] = {
                        "description": "",
                        "agents": [],
                        "entry_predicates": [],
                        "exit_predicates": [],
                        "logic": [],
                        "terminal": False,
                    }

            elif token.get("type") == "paragraph" and current_stage:

                text = self._extract_text(token)

                if text.startswith("Description"):
                    stages[current_stage]["description"] = text

                if "Terminal: true" in text:
                    stages[current_stage]["terminal"] = True

            elif token.get("type") == "list" and current_stage:

                for item in token.get("children", []):

                    line = self._extract_text(item)

                    if "Required Agents" in line:

                        agents = re.findall(r'"([^"]+)"', line)
                        stages[current_stage]["agents"].extend(agents)

                    elif "Entry Predicates" in line:

                        preds = self._find_codes(item)
                        stages[current_stage]["entry_predicates"].extend(preds)

                    elif "Exit Predicates" in line:

                        preds = self._find_codes(item)
                        stages[current_stage]["exit_predicates"].extend(preds)

                    elif "IF" in line or "ALLOW" in line:
                        stages[current_stage]["logic"].append(line)

        return stages

    # ---------------------------------------------------------
    # Transition Parser
    # ---------------------------------------------------------

    def _parse_transitions(self, logic: List[str]) -> List[Tuple[Any, str]]:

        transitions = []

        for line in logic:

            m = self.TRANSITION_PATTERN.search(line)

            if m:
                cond = m.group("condition")
                target = m.group("target")

                compiled = self.policy_registry.compile(cond)

                transitions.append((compiled, target))
                continue

            m = self.ALWAYS_PATTERN.search(line)

            if m:
                target = m.group("target")
                transitions.append((self.policy_registry.compile("True"), target))

        return transitions

    # ---------------------------------------------------------
    # Runtime Execution
    # ---------------------------------------------------------

    def determine_next_stage(self, stage: str, artifact: Dict, ctx: Dict) -> str:

        transitions = self.registry.get_transitions(stage)

        for cond, target in transitions:

            if self.policy_registry.evaluate(cond, artifact, ctx):
                logger.info(f"Transition: {stage} -> {target}")
                return target

        return "block"

    def evaluate_entry_conditions(self, stage: str, artifact: Dict, ctx: Dict):

        conds = self.registry.entry_conditions(stage)

        return all(self.policy_registry.evaluate(c, artifact, ctx) for c in conds)

    def evaluate_exit_conditions(self, stage: str, artifact: Dict, ctx: Dict):

        conds = self.registry.exit_conditions(stage)

        return all(self.policy_registry.evaluate(c, artifact, ctx) for c in conds)

    # ---------------------------------------------------------
    # AST Utilities
    # ---------------------------------------------------------

    def _extract_text(self, token) -> str:

        if token.get("type") in ("text", "codespan"):
            return token.get("raw", "")

        parts = []
        for c in token.get("children", []):
            parts.append(self._extract_text(c))

        return " ".join(p for p in parts if p)

    def _find_codes(self, token):

        results = []

        if token.get("type") == "codespan":
            results.append(token["raw"])

        for c in token.get("children", []):
            results.extend(self._find_codes(c))

        return results

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _is_terminal_stage(self, stage_name: str, block_data: Dict) -> bool:
        """
        Determines whether a stage is terminal.
        Looks for either stage name being 'block' or 'terminal',
        or if the block_data explicitly indicates terminal.
        """
        if stage_name.lower() in ["block", "terminal"]:
            return True

        # Optional: check block_data for a "Terminal: true" flag
        if block_data.get("terminal", False):
            return True

        return False