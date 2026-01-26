from pathlib import Path

# from runtime.graph.stage_graph import StageGraph

from llm.model_manager import ModelManager

#from runtime.agent_factory import AgentFactory 
# from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
# from runtime.tool_registry import ToolRegistry
from runtime.workspace_loader import WorkspaceLoader

from runtime.policy_registry import PolicyRegistry

#from runtime.pipeline.pipeline_adapter import PipelineAdapter

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class StageManager:
    """
    Maintains compiled LangGraph graphs per workspace.
    Handles caching and invalidation for reloads.
    """

    def __init__(
        self,
        workspace_path: Path,
        #agent_registry: AgentRegistry,
        #stage_registry: StageRegistry,
        #tool_registry: ToolRegistry,
        #domain_manager: DomainManager,
        hitl_callback: Optional[Any] = None
    ):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name

        #self.agent_registry = agent_registry
        #self.stage_registry = stage_registry
        #self.tool_registry  = tool_registry

        #self.model_manager = model_manager

        self.hitl_callback = hitl_callback

        self._stage_graphs = {}


    # ------------------------------------------------------------------
    # Register Stages
    # ------------------------------------------------------------------
    def register_stages(self):

        logger.info(f"Register Stage Policies")
        self.predicates = PolicyRegistry()

        # Initializing the Stage Registry
        logger.info(f"Now register Stages")
        self.stage_registry = StageRegistry( self.workspace_path)
        self.stage_registry.load_stages(self.predicates)
        logger.info(f"Stages registered: {self.stage_registry.list_stages()}")
        logger.info(f"Prospect Agents: {self.stage_registry.all_allowed_agents()}")


    def get_policy(self):
        return self.predicates

    # ------------------------------------------------------------------
    # Get Stage
    # ------------------------------------------------------------------
    def first_stage(self):
        return self.stage_registry.first_stage()

    # ------------------------------------------------------------------
    # Get First Stage
    # ------------------------------------------------------------------
    def get_stage(self, stage_name: str):
        return self.stage_registry.get(stage_name)

    # ------------------------------------------------------------------
    # Get List of Stages
    # ------------------------------------------------------------------
    def list_stages(self) -> List[str]:
        return list(self.stage_registry.list_stages())

    def get(self, workspace_name: str):
        logger.info(f"Get Stage: {workspace_name}")
        logger.info(f"Stage_name: {self._stage_graphs}")
        stage_name = self._stage_graphs[workspace_name]
        logger.info(f"Stage_name: {self._stage_graphs}")
        return self.stage_registry.get(stage_name)

    def invalidate(self, workspace_name: str):
        if workspace_name in self._stage_graphs:
            del self._stage_graphs[workspace_name]
            logger.info(f"Invalidated cached graph for workspace: {workspace_name}")
