from typing import Dict, Any, Union
from dataclasses import asdict

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import ArtifactSchema, AgentContext
from runtime.engine.domain.task import Task
from runtime.engine.domain.envelopes import DataEnvelope, ToolEnvelope
from runtime.engine.state.state_mapper import to_task, to_storage, to_agent_context, to_hitl_state

from runtime.artifact_factory import ArtifactFactory 
from runtime.agent_profiler import AgentProfile
from runtime.domain_manager import SystemContext
from runtime.stage_manager import StageManager
from runtime.agent_manager import AgentManager
from llm.model_manager import ModelManager

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

# -----------------------------------------------------------------------------
# AgentPlanner
# -----------------------------------------------------------------------------
# Control-plane supervisor responsible for plan reconciliation and stage flow.
#
# AgentPlanner:
#   - Evaluates stage exit conditions and advancement rules
#   - Determines the next stage based on the StageContract
#   - Reviews recent ToolEnvelopes as execution evidence
#   - Updates the Markdown control artifact (control_raw)
#
# This component represents the "mind" of the system:
#   it reasons about progress, correctness, and next steps,
#   but never executes tools or mutates the data plane directly.
# -----------------------------------------------------------------------------

class AgentPlanner:
    def __init__(self, context: SystemContext, stage_manager: StageManager, agent_manager: AgentManager, llm: ModelManager):

        self.context = context
        self.stage_manager = stage_manager
        self.agent_manager = agent_manager
        self.llm = llm # Usually a smarter model like GPT-4o or Gemini Pro

        self.predicates = stage_manager.get_policy()

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentPlanner is being called                                 ******")
        logger.info("*********************************************************************************************************")


        logger.info(f"State: {state}")

        if state.active_agent is None:

            logger.info("This is the first iteration ... So acquiring the first stage and first agent ...")

            return await self.compose_initial_plan(state)
 
        logger.info(f"Beyond the first Iteration: agent: {state.active_agent}, stage: {state.stage}, task {state.task}")

        stage_meta = self.stage_manager.get(state.stage)

        # ----------------------------------------------------------
        # 1. Determine exit condition to transition to next stage
        # ----------------------------------------------------------
        logger.info(f"Determine exit condition to transition to next stage [validate_route_exit_condition].")
        next_stage = self.validate_route_exit_condition(state)
        if next_stage:
            logger.info(f"It appears we have to transition to next stage:{next_stage}")
            return next_stage

        if not next_stage:
            logger.info(f"No transition to next stage yet ...")
            next_stage = state.stage

        logger.info(f"Current Stage {state.stage},  Next Stage: {next_stage}")

        # ---------------------------------------------------------------------
        # 2. Determine if there are more open tasks to complete for this agent
        # ----------------------------------------------------------------------
        logger.info(f"Determine if there are more open tasks to complete for this agent [validate_route_next_open_task].")
        next_task =  self.validate_route_next_open_task(state)
        if next_task:
            logger.info(f"It appears we have a next task to complete:{next_task}")
            return next_task

        # ------------------------------------------------------------------------
        # 4. If no open task or no next agent, then let's transition to next stage
        # -------------------------------------------------------------------------
        logger.info(f"Switch to the agent context [switch_agent_context]")
        state_ctx = self.switch_agent_context(state)

        logger.info(f"Determine Next Stages: {stage_meta.next_stages}")
        for transition in stage_meta.next_stages:
            logger.info(f"Transition (next stage): {transition}")
            if transition.get("condition") is None:
                logger.info(f"[AgentPlanner] Transitioning to stage '{transition.get("name")}' (unconditional)")
                return self.route_next_stage(state, transition.get("name"))

            compiled_condition = self.predicates.compile(transition.get("condition"))
            condition_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=state.control_raw.model_dump(),
                state_ctx=state_ctx
            )
            logger.info(f"[AgentPlanner] Transition '{transition.get("name")}' condition '{transition.get("condition")}' evaluated to {condition_result}")
            if condition_result:
                return self.route_next_stage(state, transition.get("name"))

        # --------------------------------------------------
        # 5. Summarize last tool executions
        # --------------------------------------------------
        last_tools = [ToolEnvelope.model_validate_json(t) for t in agent_ctx.tool_raw[-5:]]  # last 5 tools
        tool_summary = "\n".join([
            f"- Tool: {t.tool_name}, Success: {t.success}, Output: {t.output or t.error}"
            for t in last_tools
        ])
        logger.debug(f"[AgentPlanner] Tool Summary:\n{tool_summary}")


        # 2. Ask LLM to update the Markdown Artifact
        prompt = f"""
        You are the System Architect. Update the Markdown checklist based on tool evidence.
        
        CURRENT PLAN:
        {state['control_raw']}
        
        EVIDENCE FROM EXECUTION PLANE:
        {tool_summary}
        
        RULES:
        - Mark tasks with [x] only if the tool output proves completion.
        - Add NEW sub-tasks if a tool error suggests a recovery step is needed.
        - Return ONLY the updated Markdown.
        """
        
        new_plan = await self.llm.ainvoke(prompt)
        
        # return {"control_raw": new_plan.content}
        return {
            "stage": "analysis",
            "agent_name": "CriticAgent",
            "task": "Stress-test the proposed architecture for scalability risks"
        }

    ###############################################################################
    # Engine Governor: Decide whether to continue mission loop
    ###############################################################################
    def _should_continue(self, state: StateSchema) -> str:

        logger.info("*******************************************************************************")
        logger.info("************* Conditional Edge: _should_continue is being called  *************")
        logger.info("*******************************************************************************")

        logger.info(f"State: {state}")

        logger.info(f"Agent: {state.active_agent}")
        logger.info(f"Stage: {state.stage}")
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




    ###############################################################################
    # Compose The Initial Plan
    ################################################################################
    async def compose_initial_plan(self, state: StateSchema):

        logger.info("Composing initial plan ...")

        #if not isinstance(state, StateSchema):
        #    state = StateSchema(**state)

        # 1. Acquire first stage
        logger.info("Acquiring the first stage")
        first_stage = self.stage_manager.get_entry_stage()
        logger.info(f"First Stage Acquired: {first_stage}")

        # 2. Find first agent
        logger.info("Acquiring the first agent")
        first_agent = self.find_the_first_agent(state.domain, first_stage)
        logger.info(f"First Agent Acquired: {first_agent}")

        portfolio = await self.retrieve_agent_portfolio(state, first_agent)
        artifact = portfolio["artifact"]

        # 3. Update stage
        artifact.current_stage = first_stage
        logger.info(f"Artifact acquired: {artifact}")

        if artifact.current_plan:
            logger.info(f"Current Plan: {artifact.current_plan}")
            artifact.open_tasks = list(artifact.current_plan)

        if not artifact.open_tasks:
            return None

        next_task = artifact.open_tasks.pop(0)
        logger.info(f"Next Task: {next_task}")

        # Create runtime AgentContext
        agent_ctx = AgentContext(
            agent_name=first_agent,
            stage=first_stage,
            control_raw=artifact,
            tool_raw=[]
        )

        # Serialize BEFORE storing in state
        state.agents[first_agent] = to_storage(agent_ctx)
        state.set_task(next_task)

        return {
            "task": state.task,
            "stage": first_stage,
            "active_agent": first_agent,
            "agents": state.agents
        }

    ###############################################################################
    # Retrieve Agent's Portfolio
    ################################################################################
    async def retrieve_agent_portfolio(self, state: Union[StateSchema, Dict[str, Any]], agent: str):

        # 3. Compose the relevent data source (data envelope) and tools (tool_envelope)
        #logger.info("Acquiring the relevant data source (data envelope)")
        #data_envelope = self.context.data_manager.get_initial_envelope(agent)

        #logger.info("Acquiring the relevant tools set (tool envelope)")
        #tool_envelope = self.context.tool_manager.get_initial_envelope(agent)

        # 4. Get agent profile to build the artifact.
        logger.info("Get the agent profile ...")
        agent_profile = self.agent_manager.get_agent_profile(agent)
        logger.info(f"Agent's Profile: {agent_profile}")

        # 5. Compose the artifact
        logger.info("Now acquiring the first task based on user intent and user profile")
        artifact = await self.build_initial_artifact(state, agent_profile)

        return { "artifact" : artifact }

    ####################################################################################################
    # Find The First Agent
    ####################################################################################################
    def find_the_first_agent(self, domain: str, first_stage: str):

        logger.info("Finding the first agent ...")

        logger.info(f"Allowed Agents: {self.stage_manager.allowed_agents(first_stage)}")

        # Acquire first agent
        first_agent = self.agent_manager.first_agent(
                self.stage_manager.allowed_agents(first_stage)
            )

        if first_agent is None:
            logger.info(f"No agent to handle the first task for stage '{stage}")
            raise Exception(f"No agent to handle the first task for stage '{stage}")

        logger.info(f"Domain: {domain}, First Stage: {first_stage}, First Agent: {first_agent}")  

        return first_agent

    ####################################################################################################
    # Build the Initial Artifact
    ####################################################################################################
    async def build_initial_artifact(self, state: Union[StateSchema, Dict[str, Any]], profile: AgentProfile) -> ArtifactSchema:

        logger.info("[AgentPlanner] Extracting the ARCHITECT_TEMPLATE.md from the repo")
        template_repo = self.context.template_repo

        if not template_repo.exists():
            logger.error(f"Workspace path '{templates_dir}' does not exist")
            raise FileNotFoundError(f"Workspace path '{templates_dir}' does not exist")

        # We load both templates
        self.architect_template = ModelManager.read_prompt_template(ModelManager.RUNTIME_TEMPLATE, "ARCHITECT_TEMPLATE.md")
    
        # Get available tools
        tools = self.context.tool_manager.list_available_tools()
        logger.info(f"List of available tools: {tools}")

        # Get corresponding input schemas
        input_schemas = self.context.data_manager.list_available_input_schemas(tools)
        logger.info(f"List of available input schemas: {input_schemas}")

        # 1. Hydrate the INSTRUCTIONS (The System Prompt)
        logger.info("[AgentPlanner] Build Phase: Hydrating the system prompt.")
        system_prompt = ModelManager.hydrate(self.architect_template, {
            "profile_name": profile.name,
            "profile_role" : profile.role,
            "profile_capabilities": profile.capabilities,
            "profile_task_style" : profile.task_style,
            "profile_can_execute_tools" : str(profile.can_execute_tools),
            "profile_forbidden_actions": profile.forbidden_actions,
            "profile_input_schema" : profile.input_schema,
            "profile_output_schema" : profile.output_schema,
            "user_intent" : state.user_intent,
            "available_tools" : str(tools),
        })
        logger.info(f"Agent Planner initial Prompt: {system_prompt}")

        # 2. Get the RAW TASKS from the LLM
        # The LLM only sees the Instructions and the Goal.

        '''
        logger.info("LLM Model Call ...")
        raw_tasks = await _call_llm(prompt=system_prompt, user_intent=state.user_intent, model_manager=self.llm)
        logger.info("LLM Model Call complete ...")

        logger.info(f"raw_tasks: {raw_tasks.content.strip()}") # Response is an AIMessage(content="...")

        task_dict = self.extract_json_from_markdown(raw_tasks.content.strip())

        logger.info(f"task dict: {task_dict}")


        for task in task_dict:
            artifact.current_plan.append(Task(
                id=task.get("id"),
                execution=task.get("execution"),
                tool_name=task.get("tool_name"),
                description=task.get("description"),
                status="pending",
                stage=state.stage
            ))
        '''

        artifact = ArtifactFactory.initialize_from_agent(profile, state.session_id)

        # Just for now temporarily
        artifact.current_plan = []
        artifact.current_plan.append(
            Task(
                id='1',
                execution='tool',
                tool_name='get_market_regime_data',
                description='Calculate the current market value of NVIDIA stock based on its historical price data and volume history.',
                status="pending",
                stage=state.stage
            )
        )
        artifact.current_plan.append(
            Task(
                id='2',
                execution='tool',
                tool_name='search_ticker_news',
                description='Search for the latest news headlines related to NVIDIA stock volatility.',
                status="pending",
                stage=state.stage
            )
        )
        artifact.current_plan.append(
            Task(
                id='3',
                execution='tool',
                tool_name='analyze_earnings_call',
                description='Analyze earnings calls of recent NVIDIA stock calls.',
                status="pending",
                stage=state.stage
            )
        )       

        logger.info(f"Initial Artifact: {artifact}")

        return artifact

    def extract_json_from_markdown(self, md: str) -> list:
        # This pattern looks for ```json (optional) ... content ... ```
        # It uses a non-greedy match (.*?) to find the first block
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
        
        if match:
            json_str = match.group(1).strip()
        else:
            # Fallback: maybe there are no fences at all
            json_str = md.strip()
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extracted string: {json_str}")
            raise e

            return json.loads(json_str)



    ###############################################################################
    # Routing To Next Open Task
    ################################################################################
    def validate_route_exit_condition(self, state: StateSchema) -> dict:

        agent_ctx = state.get_active_agent()  

        logger.info(f"Current Stage: {state.stage}")
        stage_meta = self.stage_manager.get(state.stage)

        logger.info(f"[AgentPlanner] Evaluating Exit Condition for stage '{state.stage}'")
        if stage_meta.exit_condition:
            logger.info(f"[AgentPlanner] Evaluate exit condition '{stage_meta.exit_condition}")

            compiled_condition = self.predicates.compile(stage_meta.exit_condition)
            logger.info(f"[AgentPlanner] Exit condition '{stage_meta.exit_condition}' and compiled: '{compiled_condition}'")

            logger.info(f"Switch to the agent context")
            state_ctx = self.switch_agent_context(state)

            exit_result = self.predicates.evaluate(
                compiled_expr=compiled_condition,
                artifact=asdict(agent_ctx.control_raw),
                state_ctx=state_ctx,
            )

            logger.info(f"[AgentPlanner] Exit Condition result: {exit_result}")
            if not exit_result:
                logger.info(f"[AgentPlanner] Stage '{state.stage}' incomplete, tackle next open task or next agent")
                return {"control_raw" : agent_ctx.control_raw }
        return None



    ###############################################################################
    # Routing To Next Open Task
    ################################################################################
    def validate_route_next_open_task(self, state: StateSchema) -> dict:

        agent_ctx = state.get_active_agent()  
        artifact = agent_ctx.control_raw

        logger.info(f"Artifact: {artifact}")

        # 1. If artifact is blocked or completed → stop
        if artifact.status in ("blocked", "completed", "aborted"):
            return {"next": "end", "reason" : artifact.status }

        # 2. If there are open tasks → route to agent runner
        if artifact.open_tasks:
            next_task = artifact.open_tasks[0]

            return {
                "next": "runner",
                "task": next_task,
                "stage": artifact.current_stage
            }

        # 3. No open tasks → re-plan or validate
        return {"next": "validator"}


    ###############################################################################
    # Routing To Next Agent
    ################################################################################
    def validate_route_next_agent(self, state: Union[StateSchema, Dict[str, Any]]) -> dict | None:
        """
        Decide which agent should run next within the current stage.
        Runs agents sequentially per stage.
        """
        stage = state.current_stage
        if not stage:
            return None

        # Agents allowed to run in this stage
        allowed_agents = self.stage_manager.allowed_agents(stage)

        # Ensure execution tracking exists
        if stage not in state.executed_agents_per_stage:
            state.executed_agents_per_stage[stage] = []

        executed = state.executed_agents_per_stage[stage]

        # Determine remaining agents for this stage
        remaining = [agent for agent in allowed_agents if agent not in executed]

        # No agents left → stage is complete
        if not remaining:
            return None

        next_agent = remaining[0]

        # Allowed: factual bookkeeping
        # Changes to this state is not carried over. It needs to be returned partially
        # but we use this for convenience
        state.executed_agents_per_stage[stage].append(agent_name)
        state.history_agents.append(agent_name)

        # Retrieve Agent's Portfolio / Suitecase
        portfolio = self.retrieve_agent_portfolio(state, first_agent)

        if state.agents[next_agent]:
           state.agents[next_agent].control_raw =  to_storage(portfolio.artifact)
           state.agents[next_agent].data_raw = to_stroage(portfolio.data_envelope)
        else:
            # When finished, next agent is created
            runner_context = AgentContext(
                agent_name=next_agent,
                stage=stage,
                control_raw=artifact,
                data_raw=data_envelope, 
                tool_raw={ tool_result }
            )
            state.agents[next_agent] = to_storage(runner_context)

        return {
            "active_agent": next_agent,
            "agents" : state.agents,
            "executed_agents_per_stage" : state.executed_agents_per_stage,
            "history_agents" : state.history_agents,
        }


    ###############################################################################################
    # Transition Phase: we advance to next stage following correct exit conditions
    ################################################################################################
    def route_next_stage(self, state: Union[StateSchema, Dict[str, Any]], next_stage: str) -> dict:
        """
        Advance the workflow to the next stage and select the first allowed agent.

        Responsibilities:
        - Update stage
        - Select the first allowed agent for the new stage
        - Reset task
        """

        logger.info(
            f"[advance] Transitioning from stage='{state.stage}' to stage='{next_stage}'"
        )

        # 1. Resolve allowed agents for next stage
        allowed_agents = self.stage_manager.allowed_agents(next_stage)
        if not allowed_agents:
            raise RuntimeError(
                f"No allowed agents registered for stage '{next_stage}'"
            )

        # 2. Select first agent deterministically
        first_agent = self.agent_manager.first_agent(allowed_agents)

        logger.info(
            f"[advance] Next stage='{next_stage}', first agent='{first_agent}'"
        )

        return {
            "stage": next_stage,
            "agent": first_agent,
            "task": None,
        }



    #########################################################################################################
    # Transfer to a new agent context.
    #    agent_context.data_raw  # DataEnvelope[RealestateSchema]
    #    ctx["data"]             # dict of RealestateSchema fields
    #    ctx["data_meta"]        # metadata of the data envelope
    #    ctx["recent_tools"]     # metadata of the tool envelope - last 5 tool executions as dicts
    #    ctx["current_stage"] = state.stage
    ##########################################################################################################
    def switch_agent_context(self, state: StateSchema) -> dict:
        """
        Build a context dictionary from a StateSchema to evaluate stage predicates.
        """
        # Basic State context
        logger.info("Building predicate state context ...")
        state_ctx = {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.stage,
            "current_agent": state.active_agent,
            "task": state.task,
            "done": state.done,
            "user_intent": state.user_intent,
            "workflow_metadata": state.workflow_metadata.copy(),
            "history_agents": state.history_agents.copy(),
            "executed_agents_per_stage": state.executed_agents_per_stage.copy(),
        }

        agent_ctx = state.get_active_agent()  

        agent_data = agent_ctx.data_raw

        # Include data envelope as dict for predicates
        if isinstance(agent_data, DataEnvelope):
            state_ctx["data"] = agent_data.payload #
            state_ctx["data_meta"] = { # metadata of the data envelope
                "tool": agent_data.tool,
                "type": agent_data.type,
                "stage": agent_data.stage,
                "producer": agent_data.producer,
                "created_at": str(agent_data.created_at),
                "checksum": agent_data.checksum,
                "references": agent_data.references.copy()
            }
        else:
            # fallback if raw dict or not typed yet
            state_ctx["data"] = agent_data
            state_ctx["data_meta"] = {}

        # Include recent tool outputs
        agent_tool = agent_ctx.tool_raw

        tool_context = []
        if isinstance(agent_tool, list):
            for t in agent_tool[-5:]:  # last 5 tool executions
                if isinstance(t, ToolEnvelope):
                    tool_context.append({ # metadata of the tool envelope
                        "name": t.tool_name,
                        "success": t.success,
                        "output": t.output,
                        "error": t.error,
                        "stage": t.stage,
                        "agent_role": t.agent_role
                    })
                elif isinstance(t, dict):
                    tool_context.append(t)
        state_ctx["recent_tools"] = tool_context

        logger.info(f"Predicate state context: {state_ctx}")

        return state_ctx


    ###############################################################################
    # Replan as required, but his may need confirmation from HITL
    ################################################################################
    def replan(self, artifact: ArtifactSchema, observation: str):
        # The Planner prompt focuses on the 'Big Picture'
        prompt = f"""
        Current Mission: {artifact.mission}
        Current Plan: {artifact.current_plan}
        New Observation: {observation}
        
        Task: Re-evaluate the open tasks. Add, remove, or re-order tasks 
        to ensure the mission succeeds. Output the updated task list as JSON.
        """
        
        # LLM provides the NEW list of tasks
        new_tasks_payload = self.llm.ainvoke(prompt, response_format=TaskListSchema)
        
        # MUTATION: The Planner updates the Data Envelope
        artifact.open_tasks = new_tasks_payload.tasks
        artifact.plan_history.append(f"Replanned at {datetime.now(UTC)}: {observation}")
