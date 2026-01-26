###########################################################################
# PipelineLinter.py - Enterprise-Grade Pipeline Linter
#
# Performs static analysis on pipeline templates to detect:
#
#    Pipeline Linter    
#    ├─ Cycle detection
#    ├─ Reachability analysis
#    ├─ Entry invariants
#    ├─ Exit invariants
#    ├─ Graph sanity checks
#    ├─ Structural errors
#    ├─ Logical inconsistencies
#    ├─ Governance violations
#    ├─ Unsafe routing patterns
#
# This runs BEFORE PipelineAdapter is allowed to execute.
###########################################################################

from typing import Dict, Any, List, Set
from collections import defaultdict, deque

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class PipelineLintError(Exception):
    pass


class PipelineLinter:
    def __init__(self, pipeline: Dict[str, Any]):
        logger.info(f"pipeline: {pipeline}")
        logger.info(f"Initializing PipelineLinter, stage_count: {len(pipeline.get("stages", []))}")

        self.pipeline = pipeline
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []

        self._graph = self._build_graph()

    ###########################
    # Public API
    ###########################

    def lint(self, fail_fast: bool = False) -> Dict[str, Any]:
        logger.info(f"Starting pipeline linting, fail_fast {fail_fast}")

        self._check_root()

        logger.info("Checking Stage Uniqueness ... ")
        self._check_stage_uniqueness()

        logger.info("Checking Stage Structure ... ")
        self._check_stage_structure()

        logger.info("Checking Stage References ... ")
        self._check_stage_references()

        logger.info("Checking Entry Invariants ... ")
        self._check_entry_invariants()

        logger.info("Checking Reachability ... ")
        self._check_reachability()

        logger.info("Checking Terminal Semantics ... ")
        self._check_terminal_semantics()

        logger.info("Checking Governance Rules ... ")
        self._check_governance_rules()

        logger.info("Checking Cycles ... ")
        self._check_cycles()

        logger.info( f"Pipeline linting completed, errors: {len(self.errors)}, warnings: {len(self.warnings)}, infos: {len(self.infos)}")
        
        if self.errors and fail_fast:
            logger.error(f"Pipeline linting failed (fail_fast enabled), errors: {self.errors}")
            raise PipelineLintError("\n".join(self.errors))

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.infos,
            "is_valid": len(self.errors) == 0,
        }

    ###########################
    # Graph Construction
    ###########################

    def _build_graph(self) -> Dict[str, Set[str]]:
        graph = defaultdict(set)

        for stage in self.pipeline.get("stages", []):
            name = stage.get("name")
            if not name:
                continue

            for nxt in stage.get("next_stages", []):
                nxt_name = nxt.get("name") if isinstance(nxt, dict) else nxt
                if nxt_name:
                    graph[name].add(nxt_name)

        return graph

    ###########################
    # Core Structural Checks
    ###########################

    def _check_root(self):
        logger.debug("Checking pipeline root structure")

        if "stages" not in self.pipeline or not isinstance(
            self.pipeline["stages"], list
        ):
            msg = "Pipeline must define a top-level 'stages' list"
            logger.error(msg)
            self.errors.append(msg)

    def _check_stage_uniqueness(self):
        logger.debug("Checking stage name uniqueness")

        names = [s.get("name") for s in self.pipeline.get("stages", [])]
        duplicates = {n for n in names if n and names.count(n) > 1}

        if duplicates:
            msg = f"Duplicate stage names detected: {duplicates}"
            logger.error(msg)
            self.errors.append(msg)

    def _check_stage_structure(self):
        logger.debug("Checking stage structure and required fields")

        for stage in self.pipeline.get("stages", []):
            stage_name = stage.get("name", "<unknown>")

            if "name" not in stage:
                msg = "Stage missing required field 'name'"
                logger.error(msg)
                self.errors.append(msg)

            if "description" not in stage:
                msg = f"Stage '{stage_name}' missing description"
                logger.warning(msg)
                self.warnings.append(msg)

            if "allowed_agents" not in stage and not stage.get("terminal", False):
                msg = f"Stage '{stage_name}' has no allowed_agents"
                logger.warning(msg)
                self.warnings.append(msg)

    def _check_stage_references(self):
        logger.debug("Checking next_stage references")

        stage_names: Set[str] = {
            s["name"] for s in self.pipeline.get("stages", []) if "name" in s
        }

        for stage in self.pipeline.get("stages", []):
            stage_name = stage.get("name", "<unknown>")

            for nxt in stage.get("next_stages", []):
                nxt_name = nxt.get("name") if isinstance(nxt, dict) else nxt

                if nxt_name not in stage_names:
                    msg = (
                        f"Stage '{stage_name}' references unknown "
                        f"next_stage '{nxt_name}'"
                    )
                    logger.error(msg)
                    self.errors.append(msg)

    ###########################
    # Entry / Exit Invariants
    ###########################

    def _check_entry_invariants(self):
        logger.debug("Checking entry invariants")

        # Use explicit entry_stage if provided, otherwise fallback to in-degree 0
        explicit_entry = self.pipeline.get("entry_stage")

        if explicit_entry:
            entry_stages = [explicit_entry]
        else:
            incoming = defaultdict(int)
            for src, targets in self._graph.items():
                for tgt in targets:
                    incoming[tgt] += 1

            entry_stages = [
                s["name"]
                for s in self.pipeline.get("stages", [])
                if incoming[s["name"]] == 0
            ]

        if len(entry_stages) != 1:
            msg = f"Pipeline must have exactly one entry stage; found {entry_stages}"
            logger.error(msg)
            self.errors.append(msg)
            return

        entry = entry_stages[0]
        stage = next(s for s in self.pipeline["stages"] if s["name"] == entry)

        if stage.get("terminal", False):
            msg = f"Entry stage '{entry}' cannot be terminal"
            logger.error(msg)
            self.errors.append(msg)

    def _check_exit_invariants(self):
        logger.debug("Checking exit invariants")

        terminals = {
            s["name"]
            for s in self.pipeline.get("stages", [])
            if s.get("terminal", False)
        }

        if not terminals:
            msg = "Pipeline must define at least one terminal stage"
            logger.error(msg)
            self.errors.append(msg)
            return

        for t in terminals:
            if self._graph.get(t):
                msg = f"Terminal stage '{t}' must not have outgoing edges"
                logger.error(msg)
                self.errors.append(msg)

    ###########################
    # Reachability Analysis
    ###########################

    def _check_reachability(self):
        logger.debug("Checking stage reachability")

        stages = {s["name"] for s in self.pipeline.get("stages", [])}
        incoming = defaultdict(int)

        for src, targets in self._graph.items():
            for tgt in targets:
                incoming[tgt] += 1

        entry = next((s for s in stages if incoming[s] == 0), None)
        if not entry:
            return

        visited = set()
        queue = deque([entry])

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            queue.extend(self._graph.get(node, []))

        unreachable = stages - visited
        if unreachable:
            msg = f"Unreachable stages detected: {unreachable}"
            logger.error(msg)
            self.errors.append(msg)

        terminals = {
            s["name"]
            for s in self.pipeline.get("stages", [])
            if s.get("terminal", False)
        }

        for stage in stages:
            if not self._can_reach_terminal(stage, terminals):
                msg = f"Stage '{stage}' cannot reach a terminal stage"
                logger.error(msg)
                self.errors.append(msg)

    def _can_reach_terminal(self, start: str, terminals: Set[str]) -> bool:
        visited = set()
        stack = [start]

        while stack:
            node = stack.pop()
            if node in terminals:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self._graph.get(node, []))

        return False

    ###########################
    # Cycle Detection
    ###########################

    def _check_cycles(self):
        logger.debug("Checking for cycles")

        visited = set()
        stack = set()

        def dfs(node):
            if node in stack:
                msg = f"Potential infinite loop detected involving stage '{node}'"
                logger.warning(msg)
                self.warnings.append(msg)
                return

            if node in visited:
                return

            visited.add(node)
            stack.add(node)

            for nxt in self._graph.get(node, []):
                dfs(nxt)

            stack.remove(node)

        for stage in self._graph:
            dfs(stage)

    ###########################
    # Terminal Semantics
    ###########################

    def _check_terminal_semantics(self):
        logger.debug("Checking terminal stage semantics")

        for stage in self.pipeline.get("stages", []):
            stage_name = stage.get("name", "<unknown>")

            if stage.get("terminal", False):
                if stage.get("next_stages"):
                    msg = (
                        f"Terminal stage '{stage_name}' must not define next_stages"
                    )
                    logger.error(msg)
                    self.errors.append(msg)

                if stage.get("exit_condition"):
                    msg = (
                        f"Terminal stage '{stage_name}' defines an exit_condition "
                        f"(ignored)"
                    )
                    logger.warning(msg)
                    self.warnings.append(msg)

    ###########################
    # Governance Rules
    ###########################

    def _check_governance_rules(self):
        logger.debug("Checking governance rules")

        for stage in self.pipeline.get("stages", []):
            stage_name = stage.get("name", "<unknown>")
            name = stage_name.lower()

            if "spec" in name and "revision" in name:
                if not stage.get("exit_condition"):
                    msg = (
                        f"Spec revision stage '{stage_name}' "
                        f"must require explicit approval"
                    )
                    logger.error(msg)
                    self.errors.append(msg)

            if stage.get("terminal", False) and name != "terminal":
                msg = (
                    f"Stage '{stage_name}' is terminal but not named 'Terminal'"
                )
                logger.info(msg)
                self.infos.append(msg)
