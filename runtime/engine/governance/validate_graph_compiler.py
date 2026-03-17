from __future__ import annotations
from typing import Dict, Set

from runtime.logger import AgentLogger
from runtime.engine.stage.stage_registry import StageRegistry

logger = AgentLogger.get_logger(component="system")


class PolicyGraphCompiler:

    def __init__(self, registry: StageRegistry):

        self.registry = registry
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ---------------------------------------------------------
    # Compile Validation
    # ---------------------------------------------------------
    def compile(self):

        logger.info("Compiling governance policy graph")

        self._validate_stage_presence()
        self._validate_transitions()
        self._validate_reachability()
        self._validate_agents()
        self._validate_terminal_states()

        if self.errors:
            for err in self.errors:
                logger.error(err)

            raise RuntimeError(
                f"Governance graph compilation failed with {len(self.errors)} errors"
            )

        for warn in self.warnings:
            logger.warning(warn)

        logger.info("Governance graph compilation successful")

    # ---------------------------------------------------------
    # Validate stages exist
    # ---------------------------------------------------------
    def _validate_stage_presence(self):

        stages = self.registry.list_stages()

        if not stages:
            self.errors.append("No stages registered in StageRegistry")

        if self.registry.get_entry_stage() not in stages:
            self.errors.append("Entry stage not registered")

    # ---------------------------------------------------------
    # Validate transitions
    # ---------------------------------------------------------
    def _validate_transitions(self):

        stages = self.registry.list_stages()

        for stage_name in stages:

            stage = self.registry.get_stage(stage_name)

            for transition in stage.transitions:

                if transition.target not in stages:

                    self.errors.append(
                        f"Stage '{stage_name}' has transition to unknown stage '{transition.target}'"
                    )

    # ---------------------------------------------------------
    # Reachability check
    # ---------------------------------------------------------
    def _validate_reachability(self):

        entry = self.registry.get_entry_stage()

        visited: Set[str] = set()

        def dfs(stage_name: str):

            if stage_name in visited:
                return

            visited.add(stage_name)

            stage = self.registry.get_stage(stage_name)

            for transition in stage.transitions:
                dfs(transition.target)

        dfs(entry)

        for stage_name in self.registry.list_stages():

            if stage_name not in visited:

                self.warnings.append(
                    f"Stage '{stage_name}' is unreachable from entry stage"
                )

    # ---------------------------------------------------------
    # Agent validation
    # ---------------------------------------------------------
    def _validate_agents(self):

        for stage_name in self.registry.list_stages():

            stage = self.registry.get_stage(stage_name)

            if not stage.allowed_agents:

                self.warnings.append(
                    f"Stage '{stage_name}' has no allowed agents"
                )

    # ---------------------------------------------------------
    # Terminal stage validation
    # ---------------------------------------------------------
    def _validate_terminal_states(self):

        for stage_name in self.registry.list_stages():

            stage = self.registry.get_stage(stage_name)

            if stage.terminal and stage.transitions:

                self.warnings.append(
                    f"Terminal stage '{stage_name}' should not define transitions"
                )
