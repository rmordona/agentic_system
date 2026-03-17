################################################################################
# AgentDomain
################################################################################
# Entry node responsible for initializing a domain execution domain and
# bootstrapping the first governance stage.
#
# Responsibilities:
#
# 1. Load domain runtime components:
#       - StageManager
#       - AgentManager
#       - PolicyRegistry
#       - GovernanceEngine
#
# 2. Initialize governance-aware stage routing.
#
# 3. Select the first agent allowed to operate in the entry stage.
#
# 4. Create the runtime AgentContext and inject it into the shared workflow state.
#
# This node executes exactly once at workflow startup.
################################################################################
from typing import Dict, Any

from runtime.logger import AgentLogger

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.state.state_mapper import to_storage
from runtime.engine.domain.agent_context import AgentContext

from runtime.domain_manager import SystemContext
from runtime.engine.stage.stage_manager import StageManager
from runtime.agent_manager import AgentManager

from runtime.engine.governance.governance_engine import GovernanceEngine
from runtime.engine.governance.governance_manager import GovernanceManager

logger = AgentLogger.get_logger(component="system")


class AgentDomain:

    def __init__(self, context: SystemContext):

        self.context = context

        #self.stage_manager: StageManager | None = None
        #self.agent_manager: AgentManager | None = None
        #self.policy_registry: PolicyRegistry | None = None
        #self.governance_engine: GovernanceEngine | None = None


    ############################################################################
    # Runtime Entry
    ############################################################################
    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentDomain is being called                                    ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"Domain Name: {state.domain_name}")
        logger.info(f"Role Name: {state.role_name}")
        logger.info(f"Active Agent: {state.active_agent}")

        # Validate domain
        if state.domain_name is None:
            return "classifier"

        # First iteration bootstrap
        if state.active_agent is None:

            logger.info("Initializing domain runtime")

            await self.initialize_domain(state.domain_name, state.role_name)

            return self.bootstrap_stage(state)

        return {}

    ############################################################################
    # Initialize Workspace Runtime
    ############################################################################
    async def initialize_domain(self, domain_name: str, role_name: str):

        logger.info(f"Initializing domain runtime: {domain_name}, {role_name}")

        # ---------------------------------------------------------------------
        # Stage Manager
        # ---------------------------------------------------------------------
        stage_manager = StageManager(domain_name, role_name)
        stage_manager.register_stages()

        logger.info("StageManager initialized")


        # ---------------------------------------------------------------------
        # Agent Manager
        # ---------------------------------------------------------------------
        agent_manager = AgentManager(domain_name, role_name)
        agent_manager.scan_and_register_agents()

        logger.info("AgentManager initialized")


        # ---------------------------------------------------------------------
        # Governance Graph
        # ---------------------------------------------------------------------
        graph = stage_manager.compile_governance_graph()

        logger.info("GovernanceGraph compiled")

        # ---------------------------------------------------------------------
        # Governance Engine
        # ---------------------------------------------------------------------
        governance_engine = GovernanceEngine(
            graph=graph,
            policy_registry=stage_manager.policy_registry
        )

        logger.info("GovernanceEngine initialized")

        # ---------------------------------------------------------------------
        # Governance Manager
        # ---------------------------------------------------------------------
        governance_manager = GovernanceManager(
            engine=governance_engine,
            policy_registry=stage_manager.policy_registry
        )

        logger.info("GovernanceManager initialized")

        # ---------------------------------------------------------------------
        # Inject into system context
        # ---------------------------------------------------------------------
        await self.context.initialize(
            domain_name=domain_name,
            role_name=role_name,
            stage_manager=stage_manager,
            agent_manager=agent_manager,
            governance_manager=governance_manager
        )

        logger.info("SystemContext initialized")

    ############################################################################
    # Bootstrap First Stage
    ############################################################################
    def bootstrap_stage(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("Bootstrapping first governance stage")

        stage_manager = self.context.stage_manager
        agent_manager = self.context.agent_manager

        # ---------------------------------------------------------------------
        # Stage
        # ---------------------------------------------------------------------
        intent = state.domain_meta.get("intent")

        logger.info(f"Domain Meta: {state.domain_meta}")

        stage_name = stage_manager.resolve_stage_for_intent(intent)


        logger.info(f"Entry stage: {stage_name}")

        # ---------------------------------------------------------------------
        # Agent
        # ---------------------------------------------------------------------

        allowed_agents = stage_manager.allowed_agents(stage_name)

        agent = agent_manager.first_agent(allowed_agents)

        logger.info(f"Selected first agent: {agent}")

        # ---------------------------------------------------------------------
        # Runtime Agent Context
        # ---------------------------------------------------------------------
        agent_ctx = AgentContext(
            agent_name=agent,
            stage_name=stage_name
        )

        state.agents[agent] = to_storage(agent_ctx)

        return {
            "stage_name": stage_name,
            "active_agent": agent,
            "agents": state.agents
        }
