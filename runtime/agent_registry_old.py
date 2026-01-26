"""
AgentRegistry is responsible for constructing and providing ImpersonatorAgent
instances for a workspace.

Agents are instantiated with their dependencies (memory context, tools,
etc.) and are reused per session unless explicitly recreated.

AgentRegistry does NOT manage execution or routing.
"""


from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional

from runtime.agent.agent_impersonator import ImpersonatorAgent
from runtime.stage_registry import StageRegistry
from runtime.runtime_context import RuntimeContext
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient
from events.event_bus import EventBus

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")
 
class AgentRegistry:
    """
    Loads all agents from:

        workspaces/<workspace>/agents/<agent_name>/skill.json

    Each directory under `agents/` represents one agent.
    """

    def __init__(
        self, 
        workspace_path: Path,
        execution_mode: str,
        stage_registry: StageRegistry,
        model_manager: ModelManager,
        tool_client: ToolClient,
        event_bus: EventBus,
        ):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.execution_mode = execution_mode
        self.model_manager = model_manager
        self.tool_client = tool_client
        self.event_bus = event_bus

        # ✅ Correct directory
        self.agents_dir = self.workspace_path / "agents"

        self._agents: Dict[str, ImpersonatorAgent] = {}
        self._roles_ordered: List[str] = []

        self.allowed_agents = stage_registry.all_allowed_agents()

    # ------------------------------------------------------------------
    # Agent Loading
    # ------------------------------------------------------------------

    def load_agents(self):
        """
        Load all agents from workspace agents directory.
        """

        self.agents_dir = self.workspace_path / "agents"
        logger.info(f"Loading agents in execution mode ({self.execution_mode}) from: {self.agents_dir}")

        if not self.agents_dir.exists():
            logger.warning(f"Agents directory does not exist: {self.agents_dir}")
            return

        for agent in self.allowed_agents:
        
            agent_path = Path(self.agents_dir / agent)
            
            logger.info(f"Registering agent: {agent}")

            if not agent_path.is_dir():
                logger.info(f"Skipping agent - '{agent}' does not exist.")
                continue

            if self.execution_mode == 'sdd':
                agent_file = agent_path / "AGENT.md"
            else:
                agent_file = agent_path / "agent.json"

            logger.info(f"Agent File: {agent_file}")

            if self.execution_mode == 'sdd':
                agent_file = agent_path / "AGENT.md"
                if not agent_file.exists():
                    logger.warning(f"Missing AGENT.md in {agent_path}")
                    continue
            else:
                agent_file = agent_path / "agent.json"
                if not agent_file.exists():
                    logger.warning(f"Missing agent.json in {agent_path}")
                    continue

            agent_name = agent_path.name 

            logger.info(f"Agent Name from Path: {agent_name}")

            try:
                # Create a MemoryContext for this agent
                runtime_context = RuntimeContext(
                    namespace=f"workspace:{self.workspace_name}",
                )

                agent = ImpersonatorAgent(
                    workspace_path=self.workspace_path,
                    agent_name=agent_name,
                    stage_meta={},          # injected later
                    runtime_context=runtime_context,   # inject context instead of manager
                    model_manager=self.model_manager,
                    tool_client = self.tool_client,
                    event_bus=self.event_bus
                )

                self.register(agent)
                logger.info(f"Loaded agent: {agent.role} ({agent_name})")

            except Exception as e:
                logger.error(
                    f"Failed to load agent from {agent_path}: {e}",
                    # exc_info=True
                )

        logger.info(f"Registered agent roles: {self.roles()}")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: ImpersonatorAgent) -> None:
        role = agent.role

        if not role:
            raise ValueError("Agent role cannot be empty")

        if role in self._agents:
            self.logger.warning(
                f"Duplicate agent role '{role}' detected. Overwriting."
            )

        self._agents[role] = agent

        if role not in self._roles_ordered:
            self._roles_ordered.append(role)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, role: str) -> Optional[ImpersonatorAgent]:
        return self._agents.get(role)

    def all(self) -> List[ImpersonatorAgent]:
        return list(self._agents.values())

    def roles(self) -> List[str]:
        return self._roles_ordered.copy()

    def exists(self, role: str) -> bool:
        return role in self._agents

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    def reload_all(self) -> None:
        logger.info("Reloading all agents...")
        self._agents.clear()
        self._roles_ordered.clear()
        self.load_agents()

    def __len__(self) -> int:
        return len(self._agents)
