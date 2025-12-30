import asyncio
from pathlib import Path

# Event, Graph, Orchestrator 
from events.event_bus import EventBus
from orchestrator.stage_registry import StageRegistry, Stage
from orchestrator.orchestrator import Orchestrator
from graph.graph import build_graph
from runtime.lifecycle import register_lifecycle_handlers

# Agents
from orchestrator.agent_registry import AgentRegistry
from agents.optimistic.agent import OptimisticAgent
from agents.critic.agent import CriticAgent
from agents.synthesizer.agent import SynthesizerAgent
from agents.booking.agent import BookingAgent

# Local LLM
from llm.local_llm import LocalLLM, LocalLLMChatModel

# Memory
from runtime.memory_schemas import SemanticMemory
from runtime.langmem_memory import LangmemAdapter
from runtime.redis_memory import RedisMemoryAdapter
from runtime.episodic_memory_manager import EpisodicMemoryManager
from runtime.semantic_memory_manager import SemanticMemoryManager

# Session
from runtime.session_control import SessionControl

class SingletonResources:
    """Holds single instances of long-lived resources."""

    # LLM client
    llm_client: LocalLLM = None
    chat_model: LocalLLMChatModel = None

    # Langmem adapter
    langmem_adapter: LangmemAdapter = None

    # Redis adapter
    redis_adapter: RedisMemoryAdapter = None

    # Session control
    session_control: SessionControl = None

    # Agent registry (singleton agents)
    agent_registry: AgentRegistry = None
    _agents_initialized = False

    # Stage registry (singleton stages)
    stage_registry: StageRegistry = None

    # Event (singleton event_bus)
    event_bus: EventBus = None

    # Semantic Memory Manager (singleton semantic_memory)
    semantic_memory_manager: SemanticMemoryManager = None

    # Episodic Memory Manager (singleton memory_manager)
    episodic_memory_manager: EpisodicMemoryManager = None

    # Orchestrator (singleton stages)
    orchestrator: Orchestrator = None

    # Human in the loop (hitl)
    hitl_callback: str = None

    @classmethod
    def get_paths(cls, agent_name: str):
        template_prompt_path = Path(f"agents/{agent_name}") / "prompt.md"
        schema_path = Path(f"agents/{agent_name}") / "schema.json"
        return str(template_prompt_path), str(schema_path)

    @classmethod
    def _register_agents(cls):
        cls.agent_registry = AgentRegistry()
        for agent_cls, name, mode in [
            (OptimisticAgent,  "optimistic",  "json"),
            (CriticAgent,      "critic",     "json"),
            (SynthesizerAgent, "synthesizer",   "json"),
            (BookingAgent,     "booking",   "json")
        ]:
            template_path, schema_path = cls.get_paths(name)
            agent =  agent_cls(
                    role=name,
                    template_path=template_path,
                    schema_path=schema_path,
                    llm=cls.llm_client,
                    output_mode=mode
                )
            agent.store_memory = cls.redis_adapter.store_memory
            agent.fetch_memory = cls.redis_adapter.fetch_memory
            cls.agent_registry.register(agent)


    @classmethod
    def _register_stages(cls):
        cls.stage_registry = StageRegistry()
        cls.stage_registry.add_stage(Stage(
            name="optimistic",
            allowed_agents=["optimistic"],
            exit_condition=lambda state:
                "optimistic" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        cls.stage_registry.add_stage(Stage(
            name="critic",
            allowed_agents=["critic"],
            exit_condition=lambda state:
                "critic" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        cls.stage_registry.add_stage(Stage(
            name="synthesis",
            allowed_agents=["synthesizer"],
            exit_condition=lambda state:
                "synthesizer" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        cls.stage_registry.add_stage(Stage(
            name="booking",
            allowed_agents=["booking"],
            exit_condition=lambda state:
                "booking" in state.get("executed_agents_per_stage", {}).get(state.get("stage"), [])
        ))
        cls.stage_registry.add_stage(Stage(
            name="final",
            allowed_agents=[],
            terminal=True,
            exit_condition=lambda state: True
        ))

    @classmethod
    def initialize_resources(cls):
        if cls._agents_initialized:
            return

        if cls.llm_client is None:
            cls.llm_client = LocalLLM(model_name="qwen2.5-coder:3b", endpoint="http://localhost:11434/api/chat")
            cls.chat_model = LocalLLMChatModel(cls.llm_client)

        if cls.langmem_adapter is None:
            #_langmem_store = InMemoryStore()
            cls.langmem_adapter =  LangmemAdapter(
                    chat_model = cls.chat_model,
                    schemas=[SemanticMemory],
                    #store=_langmem_store
            )
        
        if cls.redis_adapter is None:
            cls.redis_adapter =  RedisMemoryAdapter(redis_url="redis://localhost:6379/0")

        if cls.session_control is None:
            # NEW: session control (runtime owns session identity)
            cls.session_control = SessionControl()

        if cls.event_bus is None:
            cls.event_bus = EventBus()

        if cls.semantic_memory_manager is None:
            cls.semantic_memory_manager = SemanticMemoryManager(
                event_bus=cls.event_bus,
                session_control=cls.session_control,
                memory_adapter=cls.langmem_adapter
            )

        if cls.episodic_memory_manager is None:
            cls.episodic_memory_manager = EpisodicMemoryManager(
                event_bus=cls.event_bus,
                session_control=cls.session_control,
                memory_adapter=cls.redis_adapter
            )

        if cls.agent_registry is None:
            cls._register_agents()

        if cls.stage_registry is None:
            cls._register_stages()

        # Stage registry, event bus, orchestrator
        register_lifecycle_handlers(cls.event_bus)

        # Pass HITL callback to graph builder
        cls.orchestrator = Orchestrator(
            event_bus=cls.event_bus,
            agent_registry=cls.agent_registry,
            stage_registry=cls.stage_registry,
            graph_builder=lambda a, s: build_graph(a, s, hitl_callback=cls.hitl_callback), 
        )

        cls._agents_initialized = True
