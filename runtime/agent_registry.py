# runtime/agent_registry.py

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Optional
from agents.skills.agent import SkillAgent
from runtime.logger import AgentLogger

class AgentRegistry:
    """
    Manages agents in a workspace.
    - Loads agents from workspace skill folders.
    - Maintains a mapping of role -> SkillAgent instance.
    - Supports lookup and dynamic reload.
    """


    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name
        self.skills_dir = self.workspace_path / "skills"
        self._agents: Dict[str, SkillAgent] = {}
        self._roles_ordered: List[str] = []

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(self.workspace_name, component="agent_registry")

        #logger = AgentRegistry.logger

    # ------------------------------------------------------------------
    # Agent Loading / Registration
    # ------------------------------------------------------------------

    def load_agents(self):
        """
        Load all agents from workspace skills directory.
        """
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return

        for skill_path in sorted(self.skills_dir.iterdir()):
            if not skill_path.is_dir():
                continue
            skill_name = skill_path.name
            try:
                agent = SkillAgent(
                    workspace_path=self.workspace_path,
                    skill_name=skill_name,
                    stage_meta={},  # stage info will be injected later by StageRegistry
                    llm=None,       # LLM will be injected by RuntimeManager
                    memory_manager=None,
                    embedding_store=None,
                    tool_client=None,
                )
                self.register(agent)
                logger.info(f"Loaded agent: {agent.role} ({skill_name})")
            except Exception as e:
                logger.error(f"Failed to load agent {skill_name}: {e}")

    def register(self, agent: SkillAgent):
        """
        Register a SkillAgent instance in the registry.
        """
        role = agent.role
        if role in self._agents:
            logger.warning(f"Agent role '{role}' already registered. Overwriting.")
        self._agents[role] = agent
        if role not in self._roles_ordered:
            self._roles_ordered.append(role)

    # ------------------------------------------------------------------
    # Lookup / Access
    # ------------------------------------------------------------------

    def get(self, role: str) -> Optional[SkillAgent]:
        return self._agents.get(role)

    def all(self) -> List[SkillAgent]:
        return list(self._agents.values())

    def roles(self) -> List[str]:
        return self._roles_ordered.copy()

    def exists(self, role: str) -> bool:
        return role in self._agents

    # ------------------------------------------------------------------
    # Reload / Update
    # ------------------------------------------------------------------

    def reload_agent(self, role: str):
        """
        Reload a single agent's artifact from disk.
        """
        skill_path = self.skills_dir / role
        if not skill_path.exists():
            logger.error(f"Cannot reload agent; skill folder missing: {skill_path}")
            return

        try:
            agent = SkillAgent(
                workspace_path=self.workspace_path,
                skill_name=role,
                stage_meta={},
                llm=None,
                memory_manager=None,
                embedding_store=None,
                tool_client=None,
            )
            self.register(agent)
            logger.info(f"Reloaded agent: {role}")
        except Exception as e:
            logger.error(f"Failed to reload agent {role}: {e}")

    def reload_all(self):
        """
        Reload all agents from disk (hot-reload).
        """
        self._agents.clear()
        self._roles_ordered.clear()
        logger.info("Reloading all agents...")
        self.load_agents()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __len__(self):
        return len(self._agents)

    def __contains__(self, role: str):
        return role in self._agents
