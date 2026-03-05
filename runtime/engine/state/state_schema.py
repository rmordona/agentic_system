from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any

from runtime.engine.state.state_mapper import to_task, to_storage, to_agent_context, to_hitl_state
from runtime.engine.domain.agent_context import AgentContext
from runtime.engine.domain.task import Task

# ------------------------------------------------------------------
# Using @dataclass in place of Pydantic's BaseModel as 
# BaseModel is not checkpoint-safe for langgraph HITL interrupts
# It's deepcopy does not copy private attributes properly.
# ------------------------------------------------------------------
class StateSchema(BaseModel):
    # -------------------------
    # Session Identity
    # -------------------------
    session_id: str          # business identity
    thread_id: str           # graph execution identity
    domain: str

    # -------------------------
    # Multi-Agent Registry
    # -------------------------
    agents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    active_agent: Optional[str] = None

    # -------------------------
    # Workflow State
    # -------------------------
    user_intent: Optional[str] = None

    # Storage-safe snapshots
    task: Optional[Dict[str, Any]] = None
    hitl: Optional[Dict[str, Any]] = None

    stage: Optional[str] = None
    final_content: str = ""
    done: bool = False

    # -------------------------
    # Execution Metadata
    # -------------------------
    workflow_metadata: Dict[str, Any] = Field(default_factory=dict)
    history_agents: List[str] = Field(default_factory=list)
    executed_agents_per_stage: Dict[str, List[str]] = Field(default_factory=dict)

    # =====================================================
    # =============== Agent API ===========================
    # =====================================================

    def register_agent(self, ctx: "AgentContext"):
        self.agents[ctx.agent_name] = to_storage(ctx)

    def get_agent(self, agent_name: str) -> "AgentContext":
        raw = self.agents.get(agent_name)
        if not raw:
            raise ValueError(f"Agent '{agent_name}' not found")
        return to_agent_context(raw)

    def activate_agent(self, agent_name: str):
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not registered")
        self.active_agent = agent_name

    def get_active_agent(self) -> "AgentContext":
        if not self.active_agent:
            raise ValueError("No active agent set")
        return self.get_agent(self.active_agent)

    def update_active_agent(self, ctx: "AgentContext"):
        if not self.active_agent:
            raise ValueError("No active agent set")
        self.register_agent(ctx)

    # =====================================================
    # =============== Task API ============================
    # =====================================================

    def set_task(self, task: "Task"):
        self.task = to_storage(task)

    def get_task(self) -> Optional["Task"]:
        if not self.task:
            return None
        return to_task(self.task)

    # =====================================================
    # =============== HITL API ============================
    # =====================================================

    def set_hitl(self, hitl: "HITLState"):
        self.hitl = to_storage(hitl)

    def get_hitl(self) -> Optional["HITLState"]:
        if not self.hitl:
            return None
        return to_hitl(self.hitl)

    model_config = {
        "arbitrary_types_allowed": False
    }


class StateSchema_old(BaseModel):
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    session_id: str          # business identity
    domain: str

    # Serialized AgentContexts only (storage-safe)
    agentContext: Dict[str, AgentContext] = {}

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    user_intent: Optional[str] = None
    task: Optional[Task] = None   

    agent: Optional[str] = None
    stage: Optional[str] = None

    final_content: str = ""
    done: bool = False

    workflow_metadata: Dict[str, Any] = Field(default_factory=dict)

    # HITL
    human_response: Optional[str] = None

    # Execution History
    history_agents: List[str] = Field(default_factory=list)
    executed_agents_per_stage: Dict[str, List[str]] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": False  # important
    }
