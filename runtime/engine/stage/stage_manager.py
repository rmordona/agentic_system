# runtime/engine/stage/stage_manager.py

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any
import re
import mistune

from core.paths import DOMAIN_ROOT
from runtime.logger import AgentLogger

from runtime.engine.stage.stage_registry import StageRegistry
from runtime.engine.stage.stage_schema import StageSchema, StageTransition
from runtime.engine.policy.policy_registry import PolicyRegistry

logger = AgentLogger.get_logger(component="system")


class StageManager:

    TRANSITION_PATTERN = re.compile(
        r"IF\s+(?P<condition>.*?)\s+ALLOW\s+(?P<target>\w+)(?:\s*\(Reason:\s*(?P<reason>.*?)\))?",
        re.IGNORECASE
    )

    CONSTRAINT_PATTERN = re.compile(
        r"-\s*(?P<key>[A-Z0-9_]+)\s*:\s*(?P<value>.+)"
    )

    def __init__(self, domain_name: str, role_name: str):

        self.domain_path = DOMAIN_ROOT / domain_name
        self.role_path = self.domain_path / "roles" / role_name
        self.stage_dir = self.role_path / "stages"

        self.registry = StageRegistry()
        self.policy_registry = PolicyRegistry(domain_name, role_name)

        self.md_parser = mistune.create_markdown(renderer="ast")

        if not self.stage_dir.exists():
            raise FileNotFoundError(f"Stage directory not found: {self.stage_dir}")

        self.global_constraints: Dict[str, Any] = {}

    # ---------------------------------------------------------
    # Resolve Stage Intent
    # ---------------------------------------------------------
    def resolve_stage_for_intent(self, intent: str) -> str:

        """
        Determine the first stage that supports the given intent.
        """

        intent = intent.lower()

        for stage_name in self.registry.list_stages():

            stage = self.registry.get_stage(stage_name)

            supported = getattr(stage, "supported_intents", [])

            if intent in supported:
                logger.info(
                    f"Intent '{intent}' routed to stage '{stage_name}'"
                )
                return stage_name

        logger.warning(f"No stage supports intent '{intent}', using entry stage")

        return self.get_entry_stage()

    # ---------------------------------------------------------
    # Resolve Allowed Agents and Create agent context
    # ---------------------------------------------------------
    def allowed_agents(self, stage_name: str) -> str:
        return self.registry.allowed_agents(stage_name)


    def create_agent_context(self, agent_name: str, stage_name: str):

        from runtime.engine.domain.agent_context import AgentContext

        return AgentContext(
            agent_name=agent_name,
            stage_name=stage_name
        )

    # ---------------------------------------------------------
    # Stage Registration
    # ---------------------------------------------------------

    def register_stages(self):

        stage_files = sorted(self.stage_dir.glob("*.md"))

        if not stage_files:
            raise RuntimeError(f"No stage files found in {self.stage_dir}")

        logger.info(f"Discovered stage files: {[f.name for f in stage_files]}")

        stage_counter = 0

        for file in stage_files:

            if file.name.lower() == "constraint.md":
                self._parse_constraints(file)
                continue

            logger.info(f"Loading stage file: {file.name}")

            raw_text = file.read_text()
            tokens = self.md_parser(raw_text)

            stages = self._group_tokens_by_stage(tokens)

            for stage_name, data in stages.items():

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
                    # new attributes
                    intents=data.get("intents", []), # this is stage's internal intent.
                    supported_intents=data.get("supported_intents", []), # This is for routing, matching user intent.
                    audit=data.get("audit", {})
                )

                self.registry.register_stage(stage, entry=(stage_counter == 0))

                logger.info(f"Stage loaded: {stage.to_dict()}")

                stage_counter += 1

        logger.info(
            f"GEP loaded: {len(self.registry.list_stages())} stages registered"
        )

        if self.global_constraints:
            logger.info(f"Global constraints loaded: {self.global_constraints}")

    # ---------------------------------------------------------
    # Parse Global Constraints
    # ---------------------------------------------------------

    def _parse_constraints(self, file: Path):

        logger.info(f"Parsing global constraints from {file.name}")

        raw_text = file.read_text()

        tokens = self.md_parser(raw_text)

        for token in tokens:

            if token.get("type") != "list":
                continue

            for item in token.get("children", []):

                text = self._extract_text(item).strip()

                match = self.CONSTRAINT_PATTERN.match(text)

                if not match:
                    continue

                key = match.group("key")
                value = match.group("value")

                try:
                    value = int(value)
                except ValueError:
                    pass

                self.global_constraints[key] = value

        logger.info(f"Parsed constraints: {self.global_constraints}")

    # ---------------------------------------------------------
    # Compile Governance Graph
    # ---------------------------------------------------------

    def compile_governance_graph(self):

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
    # Transition Parsing
    # ---------------------------------------------------------

    def _parse_transitions(
        self,
        logic_strings: List[str],
    ) -> List[StageTransition]:

        transitions = []

        for logic in logic_strings:

            logic = logic.strip()

            match = self.TRANSITION_PATTERN.search(logic)

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

        stages: dict[str, Any] = {}
        current_stage = None
        current_section = None

        for token in tokens:

            token_type = token.get("type")
            text = self._extract_text(token).strip()

            # ------------------------------------------
            # Stage Header
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
                    "terminal": False,
                    "intents": [],
                    "audit": {},
                    "supported_intents": [],

                    # extended metadata (not required by StageSchema)
                    "context_inputs": [],
                    "artifacts": [],
                    "timeout_seconds": None,
                    "retry_policy": {}
                }

                current_section = None
                continue

            if not current_stage:
                continue

            # ------------------------------------------
            # Section Detection
            # ------------------------------------------

            if "Required Agents" in text:
                current_section = "agents"
                continue

            if "Entry Predicates" in text:
                current_section = "entry"
                continue

            if "Exit Predicates" in text:
                current_section = "exit"
                continue

            if "Context Inputs" in text:
                current_section = "context"
                continue

            if "Artifacts Produced" in text:
                current_section = "artifacts"
                continue

            if "Transition Logic" in text:
                current_section = "logic"
                continue

            if "Retry Policy" in text:
                current_section = "retry"
                continue

            if "Timeout Seconds" in text:
                current_section = "timeout"
                continue

            if "Supported Intents" in text:
                current_section = "supported_intent"
                continue

            if "Audit" in text:
                current_section = "audit"
                continue

            if "Intent" in text:
                current_section = "intent"
                continue

            # ------------------------------------------
            # Paragraph Parsing
            # ------------------------------------------

            if token_type == "paragraph":

                kv_data = self._parse_paragraph_kv(text)

                if kv_data["description"]:
                    stages[current_stage]["description"] = kv_data["description"]

                if kv_data["policy_type"]:
                    stages[current_stage]["policy_type"] = kv_data["policy_type"]

                if kv_data["priority"]:
                    stages[current_stage]["priority"] = kv_data["priority"]

                if kv_data["terminal"] is not None:
                    stages[current_stage]["terminal"] = kv_data["terminal"]

                continue

            # ------------------------------------------
            # Lists
            # ------------------------------------------

            if token_type == "list":

                for item in token.get("children", []):

                    expr = self._extract_text(item).strip()

                    if not expr:
                        continue

                    if current_section == "agents":
                        stages[current_stage]["agents"].append(expr)

                    elif current_section == "entry":
                        if expr.lower() != "none":
                            stages[current_stage]["entry_predicates"].append(expr)

                    elif current_section == "exit":
                        stages[current_stage]["exit_predicates"].append(expr)

                    elif current_section == "context":
                        stages[current_stage]["context_inputs"].append(expr)

                    elif current_section == "artifacts":
                        stages[current_stage]["artifacts"].append(expr)

                    elif current_section == "logic":
                        stages[current_stage]["logic"].append(expr)

                    elif current_section == "retry":

                        if "Max Retries" in expr:
                            value = expr.split(":")[1].strip()
                            stages[current_stage]["retry_policy"]["max_retries"] = int(value)

                        elif "Retry Delay Seconds" in expr:
                            value = expr.split(":")[1].strip()
                            stages[current_stage]["retry_policy"]["retry_delay"] = int(value)

                    elif current_section == "intent":
                        stages[current_stage]["intents"].append(expr)

                    elif current_section == "supported_intent":
                        stages[current_stage]["supported_intents"].append(expr)

                    elif current_section == "audit":
                        # Simple parser: key: value pairs in audit
                        if ":" in expr:
                            key, value = expr.split(":", 1)
                            key = key.strip()
                            value = value.strip()

                            # Convert some fields
                            if value.lower() in ["true", "false"]:
                                value = value.lower() == "true"
                            elif value.isdigit():
                                value = int(value)

                            # For lists (comma-separated)
                            elif "," in value:
                                value = [v.strip() for v in value.split(",")]

                            stages[current_stage]["audit"][key] = value

            # ------------------------------------------
            # Timeout Parsing
            # ------------------------------------------

            if current_section == "timeout":

                try:
                    stages[current_stage]["timeout_seconds"] = int(text)
                except:
                    pass

        return stages

    # ---------------------------------------------------------
    # Helper: parse key-value pairs in paragraph
    # ---------------------------------------------------------
    def _parse_paragraph_kv(self, text: str):

        result = {
            "description": None,
            "policy_type": None,
            "priority": None,
            "terminal": None
        }

        for match in re.finditer(
            r"(Description|Policy Type|Priority|Terminal)\s*:\s*(.+?)(?=(\n|$|Description:|Policy Type:|Priority:|Terminal:))",
            text,
            flags=re.DOTALL,
        ):

            key, value = match.group(1), match.group(2).strip()

            if key == "Description":
                result["description"] = value

            elif key == "Policy Type":
                result["policy_type"] = value

            elif key == "Priority":
                try:
                    result["priority"] = int(value)
                except:
                    result["priority"] = 1

            elif key == "Terminal":
                result["terminal"] = value.lower() == "true"

        return result

    # ---------------------------------------------------------
    # Extract text from AST
    # ---------------------------------------------------------

    def _extract_text(self, token: dict) -> str:

        if token.get("type") in ("text", "codespan"):
            return token.get("raw", "")

        return " ".join(
            self._extract_text(child)
            for child in token.get("children", [])
        )

    # ---------------------------------------------------------
    # Runtime Execution
    # ---------------------------------------------------------

    def get_entry_stage(self) -> str:
        return self.registry.get_entry_stage()

    def get_stage(self, name: str):

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

            logger.info(f"Transition: {current_stage} -> {next_stage}")

            return next_stage

        return "block"
