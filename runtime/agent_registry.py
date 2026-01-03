"""
AgentRegistry is responsible for constructing and providing SkillAgent
instances for a workspace.

Agents are instantiated with their dependencies (memory context, tools,
etc.) and are reused per session unless explicitly recreated.

AgentRegistry does NOT manage execution or routing.
"""


from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from agents.skills.agent import SkillAgent

from runtime.runtime_context import RuntimeContext
from llm.model_manager import ModelManager
from runtime.tools.tool_client import ToolClient
from events.event_bus import EventBus

from runtime.logger import AgentLogger



 
class AgentRegistry:
    """
    Loads all agents from:

        workspaces/<workspace>/agents/<agent_name>/skill.json

    Each directory under `agents/` represents one agent.
    """

    def __init__(
        self, 
        workspace_path: Path,
        model_manager: ModelManager,
        tool_client: ToolClient,
        event_bus: EventBus,
        ):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        self.model_manager = model_manager
        self.tool_client = tool_client
        self.event_bus = event_bus

        # ✅ Correct directory
        self.agents_dir = self.workspace_path / "agents"

        self._agents: Dict[str, SkillAgent] = {}
        self._roles_ordered: List[str] = []

        global logger
        logger = AgentLogger.get_logger(self.workspace_name, component="agent_registry")

    # ------------------------------------------------------------------
    # Agent Loading
    # ------------------------------------------------------------------

    def load_agents(self):
        """
        Load all agents from workspace agents directory.
        """
        self.agents_dir = self.workspace_path / "agents"
        logger.info(f"Loading agents from: {self.agents_dir}")

        if not self.agents_dir.exists():
            logger.warning(f"Agents directory does not exist: {self.agents_dir}")
            return

        for agent_dir in sorted(self.agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue

            skill_file = agent_dir / "skill.json"
            logger.info(f"agent_dir: {agent_dir}")
            logger.info(f"skill_file: {skill_file}")

            if not skill_file.exists():
                logger.warning(f"Missing skill.json in {agent_dir}")
                continue

            skill_name = agent_dir.name  # 🔑 THIS IS THE ONLY NAME WE NEED

            try:
                # Create a MemoryContext for this agent
                runtime_context = RuntimeContext(
                    #memory_manager=self.memory_manager,
                    namespace=f"workspace:{self.workspace_name}",
                )

                agent = SkillAgent(
                    workspace_path=self.workspace_path,
                    skill_name=skill_name,
                    stage_meta={},          # injected later
                    runtime_context=runtime_context,   # inject context instead of manager
                    model_manager=self.model_manager,
                    tool_client=self.tool_client,
                    event_bus=self.event_bus
                )
                self.register(agent)
                logger.info(f"Loaded agent: {agent.role} ({skill_name})")

            except Exception as e:
                logger.error(
                    f"Failed to load agent from {agent_dir}: {e}",
                    exc_info=True
                )


        logger.info(f"Registered agent roles: {self.roles()}")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: SkillAgent) -> None:
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

    def get(self, role: str) -> Optional[SkillAgent]:
        return self._agents.get(role)

    def all(self) -> List[SkillAgent]:
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
