from agents.optimistic.agent import OptimisticAgent
from agents.critic.agent import CriticAgent
from agents.synthesizer.agent import SynthesizerAgent
from orchestrator.registry import AgentRegistry
from orchestrator.memory import Memory
from orchestrator.orchestrator import Orchestrator
from llm.mock import MockLLM

llm = MockLLM()

registry = AgentRegistry()
registry.register(OptimisticAgent("optimistic", "prompts/optimistic.md", "schemas/optimistic.json", llm))
registry.register(CriticAgent("critic", "prompts/critic.md", "schemas/critic.json", llm))
registry.register(SynthesizerAgent("synthesizer", "prompts/synthesizer.md", "schemas/synthesizer.json", llm))

memory = Memory(task="Design a mobile app that helps people build better habits")

orchestrator = Orchestrator(registry, memory)
orchestrator.run()

