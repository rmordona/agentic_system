from pathlib import Path

from runtime.agent_factory import AgentSchema, AgentRunner
from runtime.stage_registry import StageRegistry
from runtime.tool_registry import ToolRegistry

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class AgentRegistry:
    def __init__(self, workspace_path: str, stage_registry: StageRegistry, tool_registry: ToolRegistry):

        self.agents_dir = workspace_path / "agents"

        self.stage_registry = stage_registry
        self.tool_registry = tool_registry

        #self.agent_factory = AgentFactory(workspace_path)
        
        # Internal cache: { agent_id: AgentSchema }
        self._schemas: Dict[str, AgentSchema] = {}

        # Agent Runners
        self._runner: Dict[str, AgentRunner] = {}

        # Pre-load the system template
        self.system_template = _preload_system_template(workspace_path)


    # Let us pre-load system template
    def _preload_system_template(self, workspace_path: str) -> str:

        system_template_dir = workspace_path / "system_templates"

        system_md_path = Path(system_template_dir / "SYSTEM_PROMPT_TEMPLATE.md")

        if not system_md_path.exists():
            logger.error("System spec not found", extra={"path": system_md_path})
            raise FileNotFoundError(f"System spec not found at {system_md_path}")

        return system_md_path.read_text(encoding="utf-8")

    # Bind an Agent to a Runner
    def get_runner(self, agent_name: str) -> AgentRunner:
        """
        The Lazy Loader: Compiles on first request, 
        then returns a Runner.
        """
        if agent_name not in self._schemas:
            md_path = self.agents_dir / f"AGENT.md"
            
            if not md_path.exists():
                raise FileNotFoundError(f"Chain-of-Custody Break: {agent_name}.md missing.")

        # Return the Runner primed with the pre-compiled schema
        return AgentRunner(self._schemas[agent_name], self.tool_registry)

    def validate_all(self, required_ids: list):
        """
        A 'Pre-flight' check to ensure all agents in the 
        pipeline are actually present and valid.
        """
        for aid in required_ids:
            self.get_agent(aid) 
        print("[✓] All required agents validated and cached.")


    # --------------------------------------------------------------------------
    # Agent Loading
    #  - Agent Registry only registers the Agent Schema.
    #    The handing of the suitecase (tasks, etc.) happens during AgentFactory
    #    The task execution happens during AgentRunner 
    # --------------------------------------------------------------------------
    def load_agents(self):
        """
        Load all agents Stage Registry
        """

        self.allowed_agents = self.stage_registry.all_allowed_agents()

        #logger.info(f"Loading agents from: {self.agents_dir}")

        if not self.agents_dir.exists():
            logger.warning(f"Agents directory does not exist: {self.agents_dir}")
            return

        for agent_name in self.allowed_agents:
        
            agent_path = Path(self.agents_dir / agent_name)
            
            #logger.info(f"Registering agent: {agent_name}")

            if not agent_path.is_dir():
                logger.info(f"Skipping agent - '{agent_name}' does not exist.")
                continue

            agent_md = agent_path / "AGENT.md"
  
            #logger.info(f"Agent File: {agent_md}")

            if not agent_md.exists():
                logger.warning(f"Missing AGENT.md in {agent_md}")
                continue
 
            try:
                # Create a MemoryContext for this agent
                #runtime_context = RuntimeContext(
                #    namespace=f"workspace:{self.workspace_name}",
                #)

                # Compile text -> Validated Schema
                self.agent_schema = self.agent_factory.compile(agent_name, str(agent_md))
                self.register(self.agent_schema)

                logger.info(f"Loaded agent: {agent_name}")

            except Exception as e:
                logger.error(
                    f"Failed to load agent from {agent_path}: {e}",
                    # exc_info=True
                )

        logger.info(f"Registered agents: {self.agents()}")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, agent: AgentSchema) -> None:

        agent_name = agent.get_id()

        if agent_name not in self._schemas:
            self._schemas[agent_name] = agent
        else:
            self.logger.warning(f"Duplicate agent name '{agent_name}' detected. Overwriting.")      

    # ------------------------------------------------------------------
    # Helper Functions
    # ------------------------------------------------------------------
    def agents(self):
        return self._schemas.keys()

    def exists(self, agent_name: str) -> bool:
        return agent_name in self._schemas

    def get(self, agent_name: str) -> Optional[AgentSchema]:
        return self._schemas.get(agent_name)

    def all(self) -> List[AgentSchema]:
        return list(self._schemas.values())

    def roles(self) -> List[str]:
        return list(self._schemas.keys())


