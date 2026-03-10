from typing import Dict, Any, Optional
from dataclasses import asdict
from runtime.logger import AgentLogger

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.state.state_mapper import to_task, to_storage, to_agent_context, to_hitl_state
from runtime.engine.domain.agent_context import AgentContext

from runtime.domain_manager import SystemContext
from runtime.stage_manager import StageSchema, StageManager
from runtime.agent_manager import AgentManager

logger = AgentLogger.get_logger(component="system")


################################################################################
# AgentDomain
################################################################################
# Domain-level orchestration node responsible for initializing and routing
# execution within a LangGraph-based multi-agent workflow.
#
# Responsibilities:
# - Determine the initial stage and active agent when the workflow begins.
# - Coordinate stage-aware agent routing using the StageManager.
# - Initialize runtime AgentContext for agents entering execution.
# - Maintain and update agent state within the shared StateSchema.
# - Bridge system configuration (SystemContext) with runtime workflow state.
#
# This node acts as the entry and routing layer between the workflow state,
# stage definitions, and agent execution pipeline.
#
# Inputs:
# - state: StateSchema containing workspace context, stage information,
#   active agent, and runtime agent metadata.
#
# Outputs:
# - Dict containing updates to workflow state such as:
#     - stage: the current or next stage of execution
#     - active_agent: the agent selected to execute next
#     - agents: updated serialized agent contexts
################################################################################
class AgentDomain:
    def __init__(self, context: SystemContext):
        self.context = context

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentDomain is being called                                    ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"State Type: {type(state)}")
        logger.info(f"State: {state}")
        logger.info(f"Workspace: {state.workspace_name}")

        # First iteration: acquire initial stage and agent
        if state.active_agent is None:
            logger.info("This is the first iteration ... So acquiring the first stage and first agent ...")

            await self.initialize_domain(state.workspace_name)

            return self.retrieve_initial_stage_agent(state)

    def retrieve_initial_stage_agent(self, state: StateSchema):

        logger.info("Retrieving initial stage and agent ...")

        # 1. Acquire first stage
        logger.info("Acquiring the first stage")
        first_stage = self.stage_manager.get_entry_stage()
        logger.info(f"First Stage Acquired: {first_stage}")

        # 2. Find first agent
        logger.info("Acquiring the first agent")
        first_agent = self.agent_manager.first_agent(
            self.stage_manager.allowed_agents(first_stage)
        )
        logger.info(f"First Agent Acquired: {first_agent}")


        # Create runtime AgentContext
        agent_ctx = AgentContext(
            agent_name=first_agent,
            stage=first_stage
        )

        # Serialize BEFORE storing in state
        state.agents[first_agent] = to_storage(agent_ctx)

        return {
            "stage": first_stage,
            "active_agent": first_agent,
            "agents": state.agents
        }

    async def initialize_domain(self, workspace_name: str):

        # --------------------------------------------------
        # 1. Stage Management
        # --------------------------------------------------
        self.initialize_stages(workspace_name)
    
        # --------------------------------------------------
        # 2. Agent Management
        # --------------------------------------------------
        self.initialize_agents(workspace_name)

        # --------------------------------------------------
        # 3. System Context
        # --------------------------------------------------
        await self.context.initialize(
            workspace_name = workspace_name,
            agent_manager = self.agent_manager
        )
        

    def initialize_stages(self, workspace_name: str):
        # -----------------------------------------------------------------
        # Load the stages for the workflow
        # -----------------------------------------------------------------
        logger.info("Initializing Stage Manager")
        self.stage_manager = StageManager(workspace_name=workspace_name)
        self.stage_manager.register_stages()
        self.context.stage_manager = self.stage_manager

        logger.info("Stage Manager initialized")

    def initialize_agents(self, workspace_name: str):       
        # -----------------------------------------------------------------
        # Load the stages for the workflow
        # -----------------------------------------------------------------
        logger.info("Initializing Agent Manager")
        self.agent_manager = AgentManager(workspace_name=workspace_name)
        self.agent_manager.scan_and_register_agents()
        self.context.agent_manager = self.agent_manager
        logger.info("Agent Manager initialized")