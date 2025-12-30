from agents.optimistic import OptimisticAgent
from agents.critic import CriticAgent
from agents.synthesizer import SynthesizerAgent
from orchestrator.registry import AgentRegistry
from orchestrator.memory import Memory
from orchestrator.orchestrator import Orchestrator
from llm.mock_llm import MockLLM

llm = MockLLM()

registry = AgentRegistry()
registry.register(OptimisticAgent(
    "optimistic",
    "prompts/optimistic.md",
    "schemas/optimistic.schema.json",
    llm
))
registry.register(CriticAgent(
    "critic",
    "prompts/critic.md",
    "schemas/critic.schema.json",
    llm
))
registry.register(SynthesizerAgent(
    "synthesizer",
    "prompts/synthesizer.md",
    "schemas/synthesizer.schema.json",
    llm
))

memory = Memory(task="Design a habit-building app")

orchestrator = Orchestrator(registry, memory)
orchestrator.run()

