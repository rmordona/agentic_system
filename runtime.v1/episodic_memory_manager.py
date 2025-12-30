import asyncio
from typing import Dict, List
from runtime.memory_schemas import ProposalMemory, CritiqueMemory, EpisodicMemory
from runtime.session_control import SessionControl
# from runtime.semantic_memory import SummarizedMemory

MEMORY_THRESHOLD = 20  # maximum number of recent memories to keep before pruning/compaction

class EpisodicMemoryManager:
    """
    Event-driven memory manager.
    Listens to stage completion events and performs:
      - Semantic compaction
      - Memory pruning
      - Storing SemanticSummaryMemory
    """

    def __init__(self, event_bus,  session_control: SessionControl, memory_adapter: RedisMemoryAdapter):
        self.event_bus = event_bus
        #self.episodic_memory = episodic_memory
        self.session_control = session_control
        self.memory_adapter = memory_adapter

        # Subscribe to stage completion
        self.event_bus.subscribe("evaluate_episodic_memory", self.on_memory_evaluate)

    async def on_memory_evaluate(self, event_data: Dict):
        """
        Triggered when a stage finishes.
        Combines optimistic and critic memories, compacts, and prunes.
        """
        session_id = event_data.get("session_id") or self.session_control.session_id
        task = event_data["task"]
        stage = event_data["stage"] # not used, stage is either "conversation" or "summary"

        # Fetch recent memories
        optimistic_memories = await self.memory_adapter.fetch_memory(session_id=session_id, task=task, agent="optimistic")
        critic_memories = await self.memory_adapter.fetch_memory(session_id=session_id, task=task, agent="critic")

        optimistic_outputs = [ProposalMemory.model_validate(m).output for m in optimistic_memories]
        critic_outputs = [CritiqueMemory.model_validate(m).output for m in critic_memories]

        combined_context = {
            "optimistic": optimistic_outputs,
            "critic": critic_outputs,
        }

        # Check if compaction is needed
        total_memories = len(optimistic_outputs) + len(critic_outputs)

        if total_memories > MEMORY_THRESHOLD:

            summary_text = await self.compact_memory(combined_context)

            # Store summarized memory
            await self.memory_adapter.store_memory(
                EpisodicMemory(
                    session_id=session_id,
                    task=task,
                    agent="episodic",
                    stage="summary",
                    category="intent",
                    summary=summary_text,
            ))

            # Prune old memories (keep last MEMORY_THRESHOLD)
            await self.prune_old_memories(session_id=session_id, task=task)

    async def compact_memory(self, combined_context: Dict[str, List[Dict]]) -> str:
        """
        Uses SemanticMemory to generate a summary from combined context.
        """
        summary = await self.generate_summary(combined_context["optimistic"], combined_context["critic"])
        return summary

    async def prune_old_memories(self, session_id: str, task: str):
        """
        Keeps only the last MEMORY_THRESHOLD memories for optimistic and critic agents.
        """
        for agent in ["optimistic", "critic"]:
            memories = await self.memory_adapter.fetch_memory(session_id=session_id, task=task, agent=agent)
            if len(memories) <= MEMORY_THRESHOLD:
                continue

            # Keep the newest MEMORY_THRESHOLD items
            memories_to_keep = memories[-MEMORY_THRESHOLD:]
            keys_to_remove = [m.get("id") for m in memories[:-MEMORY_THRESHOLD] if m.get("id")]

            for key in keys_to_remove:
                # Remove old memory from Redis
                await self.semantic_memory.redis.delete(f"{session_id}:{key}")


    async def generate_summary(
        optimistic_input_context: List[Dict[str, Any]],
        critic_input_context: List[Dict[str, Any]],
        ) -> str:
            """
            Compact optimistic and critic outputs into a single semantic summary.
            Uses a system prompt to separate contexts.
            """

            system_prompt = SystemMessage(
                content=(
                    "You are a session-level memory compactor. "
                    "Summarize the outputs of multiple agents into a concise, actionable session memory.\n\n"
                    "Optimistic agent outputs:\n"
                    f"{optimistic_input_context}\n\n"
                    "Critic agent outputs:\n"
                    f"{critic_input_context}\n\n"
                    "Produce a structured summary highlighting key ideas, decisions, and rationales. "
                    "The summary should be clear, concise, and easy to reference for future agents."
                )
            )

            # Optionally, you could also add a HumanMessage if needed
            messages: List[BaseMessage] = [system_prompt]

            # Generate compacted summary
            result = await chat_model._agenerate(messages)

            # Extract text
            return result.generations[0].message.content


