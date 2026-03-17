from __future__ import annotations
from core.paths import DOMAIN_ROOT

import inspect
import importlib.util
from pathlib import Path
from typing import Dict, List


from runtime.agent_profiler import AgentProfile, AgentProfiler

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class RegisteredAgent:
    """
    Lightweight container for a registered agent.
    Holds the agent name and raw AGENT.md prompt.
    """

    def __init__(self, agent_name: str, prompt: str, source_path: Path):
        self.agent_name = agent_name
        self.prompt = prompt
        self.source_path = source_path
        
    def set_profile(self):
        pass
    def get_profile(self):
        pass


class AgentManager:
    """
    Discovers and registers agents from the filesystem.

    Each subfolder under `workspace/agent/` represents one agent.
    The folder name is used as the agent_name.
    The AGENT.md file inside is loaded as the agent's prompt.
    """

    def __init__(self, domain_name: str, role_name: str):
        self.domain_path = DOMAIN_ROOT / domain_name
        self.role_path = self.domain_path / "roles" / role_name
        self.agents_dir = self.role_path / "agents"
        self._registry: Dict[str, RegisteredAgent] = {}
        self._profiles: Dict[str, AgentProfile] = {}
        self.input_schema: dict = {}
        self.output_schema: dict = {}

    def scan_and_register_agents(self) -> None:
        """
        Scan subfolders and register agents.
        """
        logger.info(f"Scanning for agents in: {self.agents_dir}")

        if not self.agents_dir.exists() or not self.agents_dir.is_dir():
            raise ValueError(f"Invalid agent base path: {self.agents_dir}")

        for subdir in self.agents_dir.iterdir():
            if not subdir.is_dir():
                continue

            agent_name = subdir.name
            agent_md_path = subdir / "AGENT.md"


            if not agent_md_path.exists():
                logger.warning(
                    f"Skipping agent '{agent_name}': AGENT.md not found"
                )
                continue

            # Register Agent
            try:
                md_text = agent_md_path.read_text(encoding="utf-8")

                self._registry[agent_name] = RegisteredAgent(
                    agent_name=agent_name,
                    prompt=md_text,
                    source_path=agent_md_path,
                )

                logger.info(f"Registered agent '{agent_name}' from {agent_md_path}")


            except Exception as e:
                logger.error(
                    f"Failed to register agent '{agent_name}': {e}",
                    exc_info=True,
                )

            # Read the Default Input Schema <--- Input and Output schema moved to ToolManager
            # We will be using this schema from a non-mcp call, e.g. producing json formats based on given 
            # input parameters (not from a multi-task agent perspective, but for a single-task agent perspective).

            # Profile the agent
            try:

                self._profiles[agent_name] = AgentProfiler._compile_md(md_text)
                #self._profiles[agent_name] = AgentProfiler._compile_md(md_text, self.input_schema, self.output_schema)

                logger.info(f"Agent '{agent_name} is now profiled: {self._profiles[agent_name].role}")

            except Exception as e:
                logger.error(
                    f"Failed to profile agent '{agent_name}': {e}",
                    exc_info=True,
                )

        logger.info(
            f"Agent scan complete. Total registered agents: {len(self._registry)}"
        )

    def get_agent_prompt(self, agent_name: str) -> str:
        """
        Return the raw AGENT.md prompt for an agent.
        """
        agent = self._registry.get(agent_name)
        if not agent:
            raise KeyError(f"Agent '{agent_name}' is not registered")
        return agent.prompt

    def get_agent_profile(self, agent_name: str) -> AgentProfile:
        """
        Return the agent's profile (parsed from AGENT.md)
        """
        profile = self._profiles.get(agent_name)
        if not profile:
            raise KeyError(f"Agent '{agent_name}' is does not have a defined profile")
        return profile 

    def list_agents(self):
        """
        List all registered agent names.
        """
        return list(self._registry.keys())

    def has_agent(self, agent_name: str) -> bool:
        return agent_name in self._registry

    def first_agent(self, allowed_agents: List[str]) -> str:
        agents = self.list_agents()
        first_agent = allowed_agents[0]
        if first_agent in agents:
            return first_agent
        raise Exception(f"{first_agent} not in the registered list")

