from pathlib import Path
from graph.stage_graph import StageGraph

from runtime.agent_registry import AgentRegistry
from runtime.stage_registry import StageRegistry
from runtime.workspace_loader import WorkspaceLoader

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class GraphManager:
    """
    Maintains compiled LangGraph graphs per workspace.
    Handles caching and invalidation for reloads.
    """

    def __init__(
        self,
        workspace_path: Path,
        agent_registry: AgentRegistry,
        stage_registry: StageRegistry,
        hitl_callback: Optional[Any] = None
    ):
        self.workspace_path = workspace_path
        self.workspace_name = workspace_path.name
        self.agent_registry = agent_registry
        self.stage_registry = stage_registry
        self.hitl_callback = hitl_callback

        self._graphs = {}

    # ------------------------------------------------------------------
    # Build / Fetch
    # ------------------------------------------------------------------

    def build(self):
        """
        Build and compile the workspace graph dynamically using StageGraph.
        Caches the compiled graph per workspace.
        """
        if self.workspace_name in self._graphs:
            logger.info(f"Returning cached graph for workspace: {self.workspace_name}")
            return self._graphs[self.workspace_name]

        # Build graph dynamically from agent registry and stage router
        logger.info("We are about to enter graph building, plus graph compilation.")
        graph = StageGraph(
            workspace_name=self.workspace_name,
            agent_registry=self.agent_registry,
            stage_registry=self.stage_registry,
            hitl_callback=self.hitl_callback
        ).compile()

        # Cache the compiled graph
        self._graphs[self.workspace_name] = graph
        logger.info(f"Graph compiled and cached for workspace '{self.workspace_name}'")

        return graph

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def get(self, workspace_name: str):
        return self._graphs[workspace_name]

    def invalidate(self, workspace_name: str):
        if workspace_name in self._graphs:
            del self._graphs[workspace_name]
            logger.info(f"Invalidated cached graph for workspace: {workspace_name}")
