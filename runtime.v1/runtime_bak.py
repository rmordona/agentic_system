import asyncio
from pathlib import Path
from orchestrator.orchestrator import Orchestrator
from events.event_bus import EventBus
from orchestrator.agent_registry import AgentRegistry
from orchestrator.stage_registry import StageRegistry, Stage
from runtime.lifecycle import register_lifecycle_handlers
from graph.graph import build_graph

# Agents
from agents.optimistic.agent import OptimisticAgent
from agents.critic.agent import CriticAgent
from agents.synthesizer.agent import SynthesizerAgent
from agents.booking.agent import BookingAgent

# Local LLM
from llm.local_llm import LocalLLM

# Memory
from runtime.memory import manage_memory_tool, search_memory_tool
from runtime.memory_manager import MemoryManager
from runtime.semantic_memory import SemanticMemory

# Session
from runtime.session_control import SessionControl

def get_paths(agent_name: str):
    template_prompt_path = Path(f"agents/{agent_name}") / "prompt.md"
    schema_path = Path(f"agents/{agent_name}") / "schema.json"
    return str(template_prompt_path), str(schema_path)



class Runtime:
    def __init__(self, hitl_callback=None, session_id: str | None = None, user_id: str | None = None):
        self.hitl_callback = hitl_callback
        self.event_bus = EventBus()
        self.llm = LocalLLM(model_name="qwen2.5-coder:3b", endpoint="http://localhost:11434/api/chat")
        self.agent_registry = AgentRegistry()
        self.stage_registry = StageRegistry()

        # NEW: session control (runtime owns session identity)
        self.session_control = SessionControl(
            session_id=session_id,
            user_id=user_id,
        )

        # Attach memory tools
        for agent in self.agent_registry.all():
            agent.manage_memory_tool = manage_memory_tool
            agent.search_memory_tool = search_memory_tool


        self.semantic_memory = SemanticMemory(chat_model=self.llm)
        self.memory_manager = MemoryManager(
            event_bus=self.event_bus,
            semantic_memory=self.semantic_memory,
            session_control=self.session_control
        )

        self._register_agents()
        self._register_stages()
        register_lifecycle_handlers(self.event_bus)

        # Pass HITL callback to graph builder
        self.orchestrator = Orchestrator(
            agent_registry=self.agent_registry,
            stage_registry=self.stage_registry,
            event_bus=self.event_bus,
            graph_builder=lambda a, s: build_graph(a, s, hitl_callback=self.hitl_callback),
            user_id=self.session_control.user_id,    
        )



    def _register_agents(self):
        for agent_cls, name, mode in [
            (OptimisticAgent,  "optimistic",  "json"),
            (CriticAgent,      "critic",      "json"),
            (SynthesizerAgent, "synthesizer", "json"),
            (BookingAgent,     "booking",     "json")
        ]:
            template_path, schema_path = get_paths(name)
            self.agent_registry.register(
                agent_cls(
                    role=name,
                    template_path=template_path,
                    schema_path=schema_path,
                    llm=self.llm,
                    output_mode=mode
                )
            )

    def _register_stages(self):
        self.stage_registry.add_stage(Stage(
            name="optimistic",
            allowed_agents=["optimistic"],
            exit_condition=lambda state:
                "optimistic" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        self.stage_registry.add_stage(Stage(
            name="critic",
            allowed_agents=["critic"],
            exit_condition=lambda state:
                "critic" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        self.stage_registry.add_stage(Stage(
            name="synthesis",
            allowed_agents=["synthesizer"],
            exit_condition=lambda state:
                "synthesizer" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        self.stage_registry.add_stage(Stage(
            name="booking",
            allowed_agents=["booking"],
            exit_condition=lambda state:
                "booking" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        self.stage_registry.add_stage(Stage(
            name="final",
            allowed_agents=[],
            terminal=True,
            exit_condition=lambda state: True
        ))

    async def run(self, user_id: str, task: str):
        session = self.session_control.create_session(user_id=self.user_id)
        
        return await self.orchestrator.run(
            task=task,
            session=session,
        )

def run(task: str):
    runtime = Runtime()
    return asyncio.run(runtime.run(task))
