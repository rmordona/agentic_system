from typing import Dict, Any, Union
from dataclasses import asdict

from runtime.engine.domain.agent_context import AgentContext
from runtime.engine.domain.task import Task
from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.envelopes import DataEnvelope, ToolEnvelope

from runtime.domain_manager import SystemContext
from runtime.stage_manager import StageSchema, StageManager
from runtime.agent_manager import AgentManager
from llm.model_manager import ModelManager

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

# -----------------------------------------------------------------------------
# AgentRunner
# -----------------------------------------------------------------------------
# Execution-plane node responsible for acting on the current plan.
#
# AgentRunner:
#   - Operates strictly within the active stage contract
#   - Executes LLM-driven actions using bound runtime tools
#   - Converts tool calls into ToolEnvelopes
#   - Mutates the Data Plane (data_raw) based on verified tool output
#
# This component represents the "hands" of the system:
#   it performs work, gathers evidence, and reports results,
#   but never decides stage transitions or governance.
# -----------------------------------------------------------------------------
class AgentRunner:
    def __init__(self, context: SystemContext, stage_manager: StageManager, agent_manager: AgentManager, llm: ModelManager):

        self.context = context

        self.stage_manager = stage_manager
        self.agent_manager = agent_manager

        # Bind the dynamic tools to the LLM
        # The LLM is "primed" with a menu of actions.
        self.llm = llm.bind_tools(context.get_runtime_tools())

    def enforce_allowed_agents(self, agent_name, stage_meta: StageSchema):
        if agent_name not in stage_meta.allowed_agents:
            raise Exception(f"{agent_name} not allowed in stage {stage_meta.name}")

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentRunner is being called                                  ******")
        logger.info("*********************************************************************************************************")

        logger.info(f"Received state from agent: '{state.active_agent}', stage: {state.stage}, task: {state.task}")

        user_intent = state.user_intent

        stage      = state.stage         # Received from AgentPlanner
        agent_name = state.active_agent  # Received from AgentPlanner
        task       = state.get_task()    # Received from AgentPlanner

        logger.info(f"Current Stage: {stage}")
        logger.info(f"Task Received: {task}")
        logger.info(f"Task: {task.id}, description: {task.description}")
        logger.info(f"Tool type: {task.execution}, tool_name: {task.tool_name}")

        stage_meta = self.stage_manager.get(stage)
        self.enforce_allowed_agents(agent_name, stage_meta)

        # Get Agent Context
        agent_ctx = state.get_active_agent()  

        # Get Agent Profile
        agent_profile = self.agent_manager.get_agent_profile(agent_name)
        logger.info(f"Agent Profile: {agent_profile}")

        # Get The Artifact for State Control
        artifact = agent_ctx.control_raw

        # Extract tasks to be executed
        artifact.open_tasks = [
            t for t in artifact.current_plan 
            if not t.get("depends_on")
        ]

        logger.info(f"Open Tasks: {len(artifact.open_tasks)}")

        # Process the Data Envelope for Input
        data_env = await self.context.data_manager.process_input(task.tool_name, agent_name, stage, user_intent)
        logger.info(f"Data Envelope with Input Data: {data_env}")
  
        # Execute Tool and retrieve the Tool Envelope
        tool_env = await self.execute_task(task, agent_ctx, data_env)
        logger.info(f"Tool Envelope: {tool_env}")

        if isinstance(tool_env, ToolEnvelope):
            agent_ctx.tool_raw.append(tool_env)  # Preserve the ToolEnvelope


        # Process the Data Envelope for Output
        data_env = await self.context.data_manager.process_output(task.tool_name, tool_env.output, data_env)
        logger.info(f"Data Envelope Type: {type(data_env)}")
        logger.info(f"Data Envelope with Output Data: {data_env}")
        if isinstance(data_env, DataEnvelope):
            agent_ctx.data_raw = data_env # Preserve the DataEnvelope
            agent_ctx.result_summary = f"Task {task.id} completed successfully"
            state.task["result"] = asdict(tool_env)
            state.task["status"] = "done"


        #logger.info(f"agent_ctx.tool_raw: {agent_ctx.tool_raw}")
        #logger.info(f"-------------------------- agentContext: {agent_ctx}")
        logger.info(f"Tool Envelope: {asdict(tool_env)}")
        logger.info(f"State Task: {state.task}")

        state.update_active_agent(agent_ctx)

        return {
            "task" : state.task,
            "agents": state.agents
        }

    async def execute_task(self, task: Task, agent_ctx: AgentContext, data_env: DataEnvelope) -> ToolEnvelope:
        """
        Execute a single task.
        Mutates task.status and task.result ONLY.
        """
        logger.info(f"Executing task {task.id}: {data_env}")


        try:
            # -------------------------------------------------
            # 1. Build execution prompt / instruction
            # -------------------------------------------------
            instruction = {
                "agent": agent_ctx.agent_name,
                "stage": agent_ctx.stage,
                "task_id": task.id,
                "payload" : data_env.payload,
                "tool_name" : task.tool_name,
                "task_description": task.description,
                "control": agent_ctx.control_raw,
                "data": agent_ctx.data_raw,
            }

            # --------------------------------------------------------------------------------------------
            # 2. Decide execution mode (tool vs LLM)
            # --------------------------------------------------------------------------------------------
            # Always have a second guardrail (_requires_tool) to assist the LLM generated (task.execution)
            result = {}
            if task.execution == "tool":
                try:
                    result =  await self._execute_with_tool(task, instruction)
                except BaseException as e:
                    logger.exception("BaseException escaped from _execute_with_tool", exc_info=e)
                    raise
            elif task.execution == "llm":
                result = await self._execute_with_llm(task, instruction)

            # -------------------------------------------------
            # 3. Persist result
            # -------------------------------------------------
            logger.info(f"Result: {result}")

            return result

        except Exception as e:
            # -------------------------------------------------
            # 4. Failure handling
            # -------------------------------------------------
            task.status = "blocked"
            task.error = str(e)

            agent_ctx.result_summary = (
                f"Task {task.id} blocked due to error: {str(e)}"
            )
        return None

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    async def _execute_with_tool(self, task: Task, instruction: dict) -> ToolEnvelope:

        logger.info(f"Entering Execution with Tools: {task.tool_name}")


        tool_adapter = await self.context.tool_manager.get_adapter(task.tool_name)
        logger.info(f"Registered tool adapter {tool_adapter}")
        if not tool_adapter:
            raise RuntimeError(f"Tool Adapter for '{tool_name}' not registered")

        return await tool_adapter.execute(task.tool_name, instruction)

    async def _execute_with_llm(self, task: Task, instruction: dict) -> dict:

        # 1. Get Agent Prompt (AGENT.md with template to input {task} and {conversation_history}).
        #    The AGENT.md also includes JSON schema for output. This will be the result as payload.
        agent_prompt = self.agent_manager.get_agent_prompt(agent_name)

        # 2. Get Data Envelope
        data_adapter = self.context.data_manager.get_adapter(agent_name)
        data_envelope = agent_ctx.data_raw # DataEnvelope.model_validate_json(state.data_raw)
        
        # 3. LLM Inference 
        prompt = self.compose_agent_prompt(state)

        logger.info(f"[AgentRunner] Prompt:  {prompt}")
        response = await self.llm.ainvoke(prompt)

        logger.info(f"Get Tool from Tool Manager: {task.tool_name}")
        response = await self.llm.complete(
            system=f"You are {instruction['agent']} executing a task.",
            user=instruction["task_description"],
            context=instruction,
        )

        return {
            "output": response,
        }


        raise RuntimeError("No suitable tool found")


    ###############################################################################
    # Composing Agent Prompt
    ###############################################################################
    def compose_agent_prompt(self, state: StateSchema):

        # Get Agent Context
        agent_ctx = state.agents[state.active_agent]

        # Get Agent Artifact
        artifact = agent_ctx.control_raw

        # Get Agent Profile
        profile = self.agent_manager.get_agent_profile(state.active_agent)

        # Pull the CURRENT STATE from Data (The Envelope)
        # We look into the payload of the envelope to see what we already know
        data_envelope = agent_ctx.data_raw.model_dump(mode='json')
        current_payload = data_envelope.get("payload") if data_envelope else {}

        logger.info(f"Payload: {current_payload}")

        # 1. Identity & Protocol (Generic)
        system_content = f"""
        ROLE: {profile.role}
        STYLE: {profile.task_style}
        
        PROTOCOL:
        - Compare MISSION to CURRENT_STATE.
        - If CURRENT_STATE is insufficient, use a TOOL to gather more data.
        - Never assume data that is not explicitly in the CURRENT_STATE.
        """

        # 2. State & Mission (The Envelope)
        user_content = f"""
        MISSION: {artifact.mission}
        
        CURRENT_STATE:
        {json.dumps(artifact.spec, indent=2)}
        
        TASKS:
        {[t.description for t in artifact.open_tasks]}

        PAYLOAD: {current_payload}
        """
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
