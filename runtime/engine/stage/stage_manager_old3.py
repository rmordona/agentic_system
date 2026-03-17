# runtime/engine/stage/stage_manager.py

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re
import mistune

from core.paths import DOMAIN_ROOT
from runtime.logger import AgentLogger

from runtime.engine.stage.stage_registry import StageRegistry
from runtime.engine.stage.stage_schema import StageSchema, StageTransition
from runtime.engine.policy.policy_registry import PolicyRegistry

logger = AgentLogger.get_logger(component="system")


class StageManager:

    '''
    TRANSITION_PATTERN = re.compile(
        r"IF\s+(?P<condition>.*?)\s+ALLOW\s+(?P<target>\w+)",
        re.IGNORECASE,
    )
    '''
    # Match: IF <condition> ALLOW <target> (Reason: <reason>)
    TRANSITION_PATTERN = re.compile(
        r"IF\s+(?P<condition>.*?)\s+ALLOW\s+(?P<target>\w+)(?:\s*\(Reason:\s*(?P<reason>.*?)\))?",
        re.IGNORECASE
    )

    def __init__(self, domain_name: str, role_name: str):

        self.domain_path = DOMAIN_ROOT /  domain_name
        self.role_path = self.domain_path / "roles" / role_name 
        self.policy_path = self.role_path / "templates" / "governance_policy.md"

        self.registry = StageRegistry()
        self.policy_registry = PolicyRegistry(domain_name, role_name)

        self.md_parser = mistune.create_markdown(renderer="ast")

        if not self.policy_path.exists():
            raise FileNotFoundError(f"GEP not found: {self.policy_path}")

    # ---------------------------------------------------------
    # Stage Registration
    # ---------------------------------------------------------
    def register_stages(self):

        raw_text = self.policy_path.read_text()
        tokens = self.md_parser(raw_text)

        stages = self._group_tokens_by_stage(tokens)

        logger.info(f"Discovered stages: {list(stages.keys())}")

        for i, (stage_name, data) in enumerate(stages.items()):
            logger.info(f"Stage: {stage_name}, Data: {data}")

            entry_conditions = [
                self.policy_registry.compile(
                    self.policy_registry.normalize(expr)
                )
                for expr in data["entry_predicates"]
            ]

            exit_conditions = [
                self.policy_registry.compile(
                    self.policy_registry.normalize(expr)
                )
                for expr in data["exit_predicates"]
            ]

            transitions = self._parse_transitions(data["logic"])

            stage = StageSchema(
                name=stage_name,
                description=data["description"],
                policy_type=data["policy_type"],
                allowed_agents=data["agents"],
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                transitions=transitions,
                terminal=stage_name.lower() in ["block", "terminal"],
                priority=data["priority"],
            )

            self.registry.register_stage(stage, entry=(i == 0))

            logger.info(f"Stage loaded: {stage.to_dict()}")

        logger.info(
            f"GEP loaded: {len(self.registry.list_stages())} stages registered"
        )

    # ---------------------------------------------------------
    # Compile Governance Graph
    # ---------------------------------------------------------
    def compile_governance_graph(self) -> GovernanceGraph:

        from runtime.engine.governance.governance_graph import (
            GovernanceGraph,
            GovernanceEdge
        )

        graph = GovernanceGraph()

        for stage_name in self.registry.list_stages():

            stage = self.registry.get_stage(stage_name)

            graph.register_node(stage_name)

            for transition in stage.transitions:

                edge = GovernanceEdge(
                    source_stage=stage_name,
                    target_stage=transition.target,
                    predicate=transition.predicate,
                    description=transition.description,
                )

                graph.register_edge(edge)

        return graph

    # ---------------------------------------------------------
    # Retrieve Allowed Agent
    # ---------------------------------------------------------
    def allowed_agents(self, stage: StageName) -> list:
        return self.registry.get_stage(stage.stage_name)

    # ---------------------------------------------------------
    # Transition Parsing
    # ---------------------------------------------------------

    def _parse_transitions(
        self,
        logic_strings: List[str],
    ) -> List[StageTransition]:

        transitions = []

        for logic in logic_strings:
            logic = logic.strip()

            # ---------------------------------------------------
            # IF condition ALLOW target
            # ---------------------------------------------------
            match = self.TRANSITION_PATTERN.search(logic)

            logger.info(f"Match: {match}")

            if match:

                cond_expr = match.group("condition").strip()
                target = match.group("target").strip()
                reason = match.group("reason") or "No reason provided"   

                normalized = self.policy_registry.normalize(cond_expr)
                compiled = self.policy_registry.compile(normalized)

                transitions.append(StageTransition(
                    predicate=compiled,
                    target=target,
                    description=reason,
                    condition_text=cond_expr
                ))

                continue

            # ---------------------------------------------------
            # ALWAYS ALLOW target
            # ---------------------------------------------------
            if "ALWAYS ALLOW" in logic:
                target = logic.split("ALLOW")[1].strip()
                compiled = self.policy_registry.compile("True")

                transitions.append(StageTransition(
                    predicate=compiled,
                    target=target,
                    description="always",
                    condition_text="True"
                ))

        return transitions

    # ---------------------------------------------------------
    # Markdown Parsing
    # ---------------------------------------------------------

    def _group_tokens_by_stage(self, tokens: list[dict]) -> dict[str, Any]:
        """
        Parse mistune AST tokens into structured stage data.

        Handles:
        - Description
        - Policy Type
        - Required Agents
        - Entry/Exit Predicates
        - Transition Logic
        - Priority
        """
        stages: dict[str, Any] = {}
        current_stage = None
        current_section = None

        for token in tokens:
            token_type = token.get("type")
            text = self._extract_text(token).strip()

            # ------------------------------------------
            # Detect Stage Header
            # ------------------------------------------
            if token_type == "heading" and "Stage:" in text:
                current_stage = text.split("Stage:")[1].strip()
                stages[current_stage] = {
                    "description": "",
                    "policy_type": "",
                    "agents": [],
                    "entry_predicates": [],
                    "exit_predicates": [],
                    "logic": [],
                    "priority": 1,
                }
                current_section = None
                continue

            if not current_stage:
                continue

            # ------------------------------------------
            # Detect Section Headers
            # ------------------------------------------
            if "Entry Predicates" in text:
                current_section = "entry"
                continue
            if "Exit Predicates" in text:
                current_section = "exit"
                continue
            if "Transition Logic" in text:
                current_section = "logic"
                continue
            if "Priority" in text:
                current_section = "priority"
                continue

            # ------------------------------------------
            # Paragraphs: Description / Policy Type / Agents
            # ------------------------------------------
            if token_type == "paragraph":
                kv_data = self._parse_paragraph_kv(text)
                if kv_data["description"]:
                    stages[current_stage]["description"] = kv_data["description"]
                if kv_data["policy_type"]:
                    stages[current_stage]["policy_type"] = kv_data["policy_type"]
                if kv_data["agents"]:
                    stages[current_stage]["agents"].extend(kv_data["agents"])
                continue

            # ------------------------------------------
            # Lists: Predicates or Transition Logic
            # ------------------------------------------
            if token_type == "list":
                for item in token.get("children", []):
                    # Extract all text in this list item as a single string
                    expr = self._extract_text(item).strip()
                    if not expr:
                        continue

                    if current_section == "entry":
                        stages[current_stage]["entry_predicates"].append(expr)
                    elif current_section == "exit":
                        stages[current_stage]["exit_predicates"].append(expr)
                    elif current_section == "logic":
                        stages[current_stage]["logic"].append(expr)
                    elif current_section == "priority":
                        try:
                            stages[current_stage]["priority"] = int(expr)
                        except ValueError:
                            stages[current_stage]["priority"] = 1

        return stages

    def _flatten_list_item(self, token: dict) -> list[dict]:
        """
        Recursively flatten all children of a list item into a single list of tokens.
        This ensures we catch plain text, not just codespans.
        """
        tokens = []
        if "children" in token:
            for child in token["children"]:
                tokens.extend(self._flatten_list_item(child))
        else:
            tokens.append(token)
        return tokens

    # ---------------------------------------------------------
    # Helper: parse key-value pairs in a paragraph
    # ---------------------------------------------------------
    def _parse_paragraph_kv(self, text: str) -> dict[str, str | list[str]]:
        """
        Parses a paragraph text into description, policy_type, agents.
        Handles multiple lines and multiple key-value pairs in a single paragraph.
        """
        result = {
            "description": None,
            "policy_type": None,
            "agents": [],
        }

        # Split by "key:" patterns (Description, Policy Type, Required Agents)
        for match in re.finditer(
            r"(Description|Policy Type|Required Agents)\s*:\s*(.+?)(?=(\n|$|Description:|Policy Type:|Required Agents:))",
            text,
            flags=re.DOTALL,
        ):
            key, value = match.group(1), match.group(2).strip()
            if key == "Description":
                result["description"] = value
            elif key == "Policy Type":
                result["policy_type"] = value
            elif key == "Required Agents":
                result["agents"].extend(re.findall(r'["\'](.*?)["\']', value))

        return result

    # ---------------------------------------------------------
    # Recursive AST search (unchanged)
    # ---------------------------------------------------------
    def _find_recursive(self, token: dict, token_type: str) -> list[dict]:
        """
        Recursively find tokens of a given type (e.g., 'codespan') in the AST subtree.
        """
        found = []
        if token.get("type") == token_type:
            found.append(token)
        for child in token.get("children", []):
            found.extend(self._find_recursive(child, token_type))
        return found


    # ---------------------------------------------------------
    # Extract text from AST node
    # ---------------------------------------------------------
    def _extract_text(self, token: dict) -> str:
        if token.get("type") in ("text", "codespan"):
            return token.get("raw", "")
        return " ".join(self._extract_text(child) for child in token.get("children", []))


    # ---------------------------------------------------------
    # Runtime Execution
    # ---------------------------------------------------------

    def get_entry_stage(self) -> str:
        return self.registry.get_entry_stage()

    def get_stage(self, name: str) -> StageSchema:

        stage = self.registry.get_stage(name)

        if not stage:
            raise KeyError(f"Unknown stage: {name}")

        return stage

    def determine_next_stage(
        self,
        current_stage: str,
        ctx_obj: Any,
        artifact: dict,
    ) -> str:

        stage = self.get_stage(current_stage)

        next_stage = stage.resolve_transition(
            self.policy_registry.evaluate,
            ctx_obj,
            artifact,
        )

        if next_stage:

            logger.info(
                f"Transition: {current_stage} -> {next_stage}"
            )

            return next_stage

        return "block"

    def can_enter(
        self,
        stage_name: str,
        ctx_obj: Any,
        artifact: dict,
    ) -> bool:

        stage = self.get_stage(stage_name)

        return stage.can_enter(
            self.policy_registry.evaluate,
            ctx_obj,
            artifact,
        )

    def can_exit(
        self,
        stage_name: str,
        ctx_obj: Any,
        artifact: dict,
    ) -> bool:

        stage = self.get_stage(stage_name)

        return stage.can_exit(
            self.policy_registry.evaluate,
            ctx_obj,
            artifact,
        )