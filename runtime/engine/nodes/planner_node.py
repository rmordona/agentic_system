from core.paths import ARCHITECT_TEMPLATE, load_template

import re
import json
from typing import Dict, Any, List
from runtime.engine.state.state_mapper import to_storage

from runtime.logger import AgentLogger
from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import AgentContext
from runtime.engine.domain.task import Task
from runtime.domain_manager import SystemContext
from runtime.agent_profiler import AgentProfile
from runtime.artifact_factory import ArtifactFactory
from llm.model_manager import ModelManager

logger = AgentLogger.get_logger(component="system")

################################################################################
# AgentPlanner
################################################################################
# Micro-level task composer node for a LangGraph-based multi-agent system.
#
# Responsibilities:
# - Generate actionable tasks for an agent based on the current stage and user intent.
# - Hydrate prompts for the LLM using agent profile, capabilities, and pipeline/skill templates.
# - Parse LLM output into structured Task objects compatible with the AgentRunner.
# - Maintain the agent’s current plan and open tasks in the artifact.
#
# Inputs:
# - state: StateSchema instance containing active agent context and user intent.
#
# Outputs:
# - Dict containing the next task for the agent to execute.
################################################################################
class AgentPlanner:
    def __init__(self, context: SystemContext, llm: ModelManager):
        self.context = context
        self.llm = llm

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentPlanner is being called                                   ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"State Type: {type(state)}")
        logger.info(f"Stage: state.stage")
        logger.info(f"State: {state}")

        agent_ctx = state.get_active_agent()
        artifact = agent_ctx.control_raw

        if not artifact.current_plan:
            logger.info("Building initial plan for agent")
            artifact.current_plan = await self._build_initial_tasks(state, agent_ctx)
            if artifact.current_plan:
                logger.info(f"Current Plan: {artifact.current_plan}")
                artifact.open_tasks = list(artifact.current_plan)

        if artifact.open_tasks:
            next_task = artifact.open_tasks.pop(0)
            state.set_task(next_task)
            agent_ctx.control_raw = artifact
            state.agents[agent_ctx.agent_name] = to_storage(agent_ctx)
            return {"task": to_storage(next_task), 
                    "stage_name": state.stage_name, 
                    "active_agent": agent_ctx.agent_name,
                    "agents" : state.agents
                }

        # Circle back to governance if tasks are depleted
        return "governance"

    async def _build_initial_tasks(self, state: StateSchema, agent_ctx: AgentContext) -> List[Task]:

        profile: AgentProfile = self.context.agent_manager.get_agent_profile(agent_ctx.agent_name)

        # tools = self.context.tool_manager.mcp_tools()
        stage = self.context.stage_manager.get_stage(state.stage_name)
        relevant_tools = await self.context.tool_manager.select_tools_by_stage_intent(stage.supported_intents)

        stage_schema = self.context.stage_manager.get_stage(state.stage_name)
        stage_goal = stage_schema.description

        # Hydrate system prompt (pipeline.md or skill.md can be incorporated here)
        system_prompt = ModelManager.hydrate( load_template(ARCHITECT_TEMPLATE), {
            "stage_goal" : stage_goal, 
            "user_intent" : state.normalized_intent,
            "profile_name" : profile.name,
            "profile_role" : profile.role,
            "profile_task_style" : profile.task_style,
            "profile_can_execute_tools" :  profile.can_execute_tools,
            "profile_forbidden_actions": profile.forbidden_actions,
            #"profile_input_schema": profile.input_schema,
            #"profile_output_schema" : profile.output_schema,
            "profile_capabilities" : profile.capabilities,
            "available_tools": relevant_tools,
        })

        retry = 0
        while True: # Retry if generated tasks are malformed
            retry = retry + 1
            logger.info(f"Calling LLM to refine user intent: {system_prompt}")
            response = await self.llm.ainvoke(system_prompt)
            raw_tasks = getattr(response, "content", str(response))
            logger.info(f"Raw LLM output: {raw_tasks}")
    
            tasks_json = self._extract_json(raw_tasks)
            tasks: List[Task] = []
            tid = 0
            for t in tasks_json:
                tool_name = t.get("tool_name")
                execution = t.get("execution")
                if tool_name and execution in ["tool", "llm"]:
                    tid = tid + 1
                    tasks.append(Task(
                        id=tid,
                        description=t.get("description"),
                        execution=t.get("execution"),
                        tool_name=t.get("tool_name"),
                        stage_name=state.stage_name,
                        status="pending"
                    ))
            if tasks or retry > 1:
                break
        return tasks

    def _extract_json(self, content: str) -> list:
        try:
            pattern = r"```(?:json)?\s*(.*?)\s*```"
            match = re.search(pattern, content, re.DOTALL)
            json_str = match.group(1) if match else content
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse task JSON: {content}")
            raise


    ###############################################################################
    # Engine Governor: Decide whether to continue mission loop
    ###############################################################################
    def _should_continue(self, state: StateSchema) -> str:

        logger.info("*******************************************************************************")
        logger.info("************* Conditional Edge: _should_continue is being called  *************")
        logger.info("*******************************************************************************")

        logger.info(f"State: {state}")

        logger.info(f"Agent: {state.active_agent}")
        logger.info(f"Stage: {state.stage_name}")
        logger.info(f"Task: {state.task}")

        # Get Agent Context
        agent_ctx = state.get_active_agent()  

        logger.info(f"Active Agent: {agent_ctx}")

        artifact = agent_ctx.control_raw

        if artifact is None:
            logger.warning("Artifact missing — routing back to planner")
            return "planner"

        open_tasks = artifact.open_tasks or []
        decision = not artifact.validation_errors and bool(open_tasks)

        logger.info(
            f"Open tasks: {open_tasks}, len: {len(open_tasks)}, decision: {decision}"
        )

        # Example routing logic
        return "runner"