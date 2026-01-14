###########################################################################
# PipelineLinter.py - Enterprise-Grade Pipeline Linter
#
# Performs static analysis on pipeline templates to detect:
# - Structural errors
# - Logical inconsistencies
# - Governance violations
# - Unsafe routing patterns
#
# This runs BEFORE PipelineAdapter is allowed to execute.
###########################################################################


from typing import Dict, Any, List, Set

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class PipelineLintError(Exception):
    pass


class PipelineLinter:
    def __init__(self, pipeline: Dict[str, Any]):
        logger.info(
            "Initializing PipelineLinter",
            extra={
                "stage_count": len(pipeline.get("stages", []))
                if isinstance(pipeline, dict)
                else "unknown"
            },
        )

        self.pipeline = pipeline
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []

    ###########################
    # Public API
    ###########################

    def lint(self, fail_fast: bool = False) -> Dict[str, Any]:
        """
        Run all lint checks and return findings.
        """
        logger.info(
            "Starting pipeline linting",
            extra={"fail_fast": fail_fast},
        )

        self._check_root()
        self._check_stage_uniqueness()
        self._check_stage_structure()
        self._check_stage_references()
        self._check_terminal_semantics()
        self._check_loops()
        self._check_governance_rules()

        logger.info(
            "Pipeline linting completed",
            extra={
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "infos": len(self.infos),
            },
        )

        if self.errors and fail_fast:
            logger.error(
                "Pipeline linting failed (fail_fast enabled)",
                extra={"errors": self.errors},
            )
            raise PipelineLintError("\n".join(self.errors))

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.infos,
            "is_valid": len(self.errors) == 0,
        }

    ###########################
    # Lint rules
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
        duplicates = {n for n in names if names.count(n) > 1}

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
                nxt_name = nxt["name"] if isinstance(nxt, dict) else nxt

                if nxt_name not in stage_names:
                    msg = (
                        f"Stage '{stage_name}' references unknown "
                        f"next_stage '{nxt_name}'"
                    )
                    logger.error(msg)
                    self.errors.append(msg)

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

    def _check_loops(self):
        """
        Detect simple cycles without terminal escape.
        """
        logger.debug("Checking for potential infinite loops")

        graph = {
            s["name"]: [
                n["name"]
                for n in s.get("next_stages", [])
                if isinstance(n, dict)
            ]
            for s in self.pipeline.get("stages", [])
            if "name" in s
        }

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

            for nxt in graph.get(node, []):
                dfs(nxt)

            stack.remove(node)

        for stage in graph:
            dfs(stage)

    def _check_governance_rules(self):
        """
        Opinionated SDD governance checks.
        """
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
