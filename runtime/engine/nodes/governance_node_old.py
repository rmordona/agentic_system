from typing import Dict, Any, Optional
from dataclasses import asdict
from runtime.logger import AgentLogger

from runtime.engine.state.state_schema import StateSchema
from runtime.engine.domain.agent_context import AgentContext

from runtime.domain_manager import SystemContext
from runtime.stage_manager import StageSchema, StageManager

logger = AgentLogger.get_logger(component="system")


###########################################################################################################################################
# AgentGovernance
###########################################################################################################################################
# Macro-level orchestration node for a LangGraph-based multi-agent system.
#
# Responsibilities: More like Goverenance Checkpoint
# - Evaluate stage exit conditions to determine workflow transitions.
# - Select the next allowed agent for the current stage.
# - Route execution to AgentRunner, AgentPlanner, or HITL as needed.
# - Maintain stage-level execution context and history.
# - Build a predicate context for evaluating conditional transitions.
#
# Inputs:
# - state: StateSchema instance containing current stage, active agent, and workflow metadata.
#
# Outputs:
# - Dict indicating next stage, next agent, and/or next task to execute.
#
# On design of the Governance Policy (GEP)
#
# This approach is the right way to build a production-grade system where failure has real-world consequences 
# (like losing money). You have essentially created a Policy-Based Agentic Workflow.
#
# To answer your question: No, this is not "standard" for hobbyist AI apps, but it is exactly how sophisticated 
# enterprise AI and high-frequency trading (HFT) systems are beginning to evolve.
# 
# Is this a unique approach?
# It is unique in the world of general LLM "chatbots," but it aligns with a high-level architecture known as 
# The Controller-Worker Pattern or State-Space Governance.
#
# 1. How it compares to "Standard" Agentic Systems:
# Most AI Systems (Standard): Use "Chains" or "Autonomous Loops." The agent decides what to do next. 
# This is risky because if the LLM gets "conflicted," it might hallucinate a path that bypasses safety checks.
#
# Your System (Unique/Advanced): The agent is blind to the next step. It only knows its current "Skill." 
# The Governance Layer (your GEP) is the only thing that holds the map. This is often called "Air-Gapped Logic."
#
# 2. Who else uses similar patterns?
# Autonomous Driving (Waymo/Tesla): The "Planning AI" might want to turn left, but a "Hard-Coded Physics Layer" 
# (the Governance) will override that if it detects an object in the way.
# 
# Palantir AIP: They use "Ontologies" and "Policies" that define exactly what an agent can and cannot do 
# based on a set of predicates.
#
# LangGraph (State Machines): As we discussed, LangGraph is the tool used to build this, but your specific GEP 
# file is the "DNA" that makes it a governed system rather than a free-roaming one.
# 
# Why this approach is "The Right One"
# Determinism in a Probabilistic World: LLMs are probabilistic (they guess). Your Governance Policy is deterministic 
# (it follows rules). By wrapping a "Guesser" in a "Rule-Follower," you get the intelligence of AI with the safety of traditional software.
#
# Auditability (The "Why"): If a trade is blocked, you don't have to guess why. You can look at the GEP and see 
# exactly which Exit Predicate failed.
# 
# The "Consensus" Circuit (Stage 3): This is your most unique and powerful feature. Most systems just take the "best" answer. 
# Your system requires Agreement. This is the same principle used in Byzantine Fault Tolerance in distributed systems.
###########################################################################################################################################
class AgentGovernance:
    def __init__(self, context: SystemContext):
        self.context = context

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:
        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentGovernance is being called                                ******")
        logger.info("*********************************************************************************************************")

        self.stage_manager = self.context.stage_manager
        self.agent_manager = self.context.agent_manager

        logger.info(f"State Type: {type(state)}")
        logger.info(f"State: {state}")
        logger.info(f"Workspace: {state.workspace_name}")

        logger.info(f"Agent: {state.active_agent}, stage: {state.stage}, task {state.task}")

        logger.info(f"Current Stage: {state.stage}, Active Agent: {state.active_agent}")

        # Evaluate task
        if state.task is None:
            logger.info(f"No Task. Directly passing to Planner.")
            return {} # No change in state, let Planner handle tasks

        # Check for next open task
        next_task = self._next_open_task(state)
        if next_task:
            logger.info(f"If Next Task, then take _next_task.")
            return {} # No change in state, let Planner handle tasks

        # Determine next agent in stage
        next_agent = self._next_agent(state)
        if next_agent:
            logger.info(f"If Next Agent, then take _next_agent.")
            return next_agent

        # Evaluate stage exit conditions
        next_stage = self._evaluate_stage_exit(state)
        if next_stage:
            logger.info(f"If Next Stage, Passing to route_to_next_stage.")
            return self._route_to_next_stage(state, next_stage)

        # Default: remain in current stage
        return {"stage": state.stage, "active_agent": state.active_agent}

    def _evaluate_stage_exit(self, state: StateSchema) -> Optional[str]:
        stage_meta = self.stage_manager.get(state.stage)
        if not stage_meta.exit_condition:
            return None
        agent_ctx = state.get_active_agent()

        compiled = self.stage_manager.compile_predicate(stage_meta.exit_condition)
        ctx = self._build_state_context(state, agent_ctx)
        artifact = asdict(agent_ctx.control_raw)
        result = self.stage_manager.evaluate_predicate(compiled, ctx, artifact)
        logger.info(f"Stage exit condition {stage_meta.exit_condition} evaluated to {result}")
        return stage_meta.next_stages[0]["name"] if result else None

    def _next_open_task(self, state: StateSchema) -> Optional[Dict[str, Any]]:
        artifact = state.get_active_agent().control_raw
        return artifact.open_tasks

    def _next_agent(self, state: StateSchema) -> Optional[Dict[str, Any]]:
        stage = state.stage
        executed = state.executed_agents_per_stage.get(stage, [])
        allowed_agents = self.stage_manager.allowed_agents(stage)
        remaining_agents = [a for a in allowed_agents if a not in executed]
        if not remaining_agents:
            return None
        next_agent = remaining_agents[0]
        state.executed_agents_per_stage.setdefault(stage, []).append(next_agent)
        state.history_agents.append(next_agent)
        return {"active_agent": next_agent, "stage": stage}

    def _route_to_next_stage(self, state: StateSchema, next_stage: str) -> Dict[str, Any]:
        allowed_agents = self.stage_manager.allowed_agents(next_stage)
        if not allowed_agents:
            raise RuntimeError(f"No allowed agents for stage {next_stage}")
        first_agent = self.agent_manager.first_agent(allowed_agents)
        return {"stage": next_stage, "active_agent": first_agent}

    def _build_state_context(self, state: StateSchema, agent_ctx: AgentContext) -> dict:
        ctx = {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.stage,
            "current_agent": state.active_agent,
            "task": state.task,
            "done": state.done,
            "user_intent": state.normalized_intent,
            "workflow_metadata": state.workflow_metadata.copy(),
            "history_agents": state.history_agents.copy(),
            "executed_agents_per_stage": state.executed_agents_per_stage.copy(),
        }
        ctx["recent_tools"] = [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in agent_ctx.tool_raw[-5:]
        ]
        if hasattr(agent_ctx.data_raw, "payload"):
            ctx["data"] = agent_ctx.data_raw.payload
        else:
            ctx["data"] = agent_ctx.data_raw
        return ctx


===============

import datetime
from typing import Any, Dict, List, Tuple
from langgraph.graph import END

class AgentGovernance:
    def __init__(self, policy_path: str):
        self.policy = self.load_policy(policy_path)

    def load_policy(self, path: str) -> Dict:
        # In a real app, this would parse your .md into a structured Dict
        # For this node, we assume it's pre-loaded
        return {
            "trade_execution": {
                "entry_predicates": [
                    "ctx['risk_metrics']['status'] == 'GREEN'",
                    "ctx['order_payload']['ticker'] == ctx['active_ticker']",
                    "self.check_time_delta(ctx['current_price']['timestamp']) < 30",
                    "self.check_slippage(ctx) < 0.02"
                ]
            }
        }

    # --- HELPER PREDICATES (The "Tweak" Logic) ---
    def check_time_delta(self, timestamp_str: str) -> float:
        """Calculates seconds elapsed since the last price update."""
        dt = datetime.datetime.fromisoformat(timestamp_str)
        delta = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds()
        return delta

    def check_slippage(self, ctx: Dict) -> float:
        """Calculates % change between analysis price and current execution price."""
        analysis_p = ctx.get("analysis_price", 0)
        current_p = ctx["current_price"].get("price", 0)
        if analysis_p == 0: return 1.0 # Fail if no baseline
        return abs(current_p - analysis_p) / analysis_p

    # --- THE NODE FUNCTION ---
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ctx = state["ctx"]
        current_stage = state["stage"]
        
        print(f"--- GOVERNANCE CHECK: {current_stage} ---")
        
        # 1. FETCH STAGE POLICY
        stage_policy = self.policy.get(current_stage)
        if not stage_policy:
            return {"next_step": "block", "error": f"No policy for {current_stage}"}

        # 2. EVALUATE ENTRY/EXIT PREDICATES
        # We iterate through the string-based rules in the GEP
        for predicate in stage_policy.get("entry_predicates", []):
            try:
                # Evaluating the predicate string against the context
                # 'self' is passed so it can call check_time_delta etc.
                result = eval(predicate, {"ctx": ctx, "self": self})
                if not result:
                    print(f"VETO: Predicate Failed -> {predicate}")
                    
                    # TRIGGER THE "STALE DATA" RE-ROUTE TWEAK
                    if "check_time_delta" in predicate:
                        return {"next_step": "macro_context", "error": "STALE_DATA_RESET"}
                    
                    return {"next_step": "block", "error": f"Predicate Failed: {predicate}"}
            except Exception as e:
                return {"next_step": "block", "error": f"Governance Runtime Error: {str(e)}"}

        # 3. TRANSITION LOGIC
        # If all predicates pass, we "Unlock" the next stage based on your GEP Transition Logic
        if current_stage == "trade_execution":
            return {"next_step": "post_trade_audit"}
        
        # Default fallback
        return {"next_step": "continue"}

# --- LANGGRAPH ROUTER FUNCTION ---
def governance_router(state: Dict):
    """
    This is the conditional edge logic that looks at what 
    the AgentGovernance node decided.
    """
    decision = state.get("next_step")
    if decision == "block":
        return "block_node"
    if decision == "macro_context":
        return "macro_node"
    return state.get("target_stage_node") # e.g., 'post_trade_node'