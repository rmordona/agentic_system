import json
from agents.base import BaseAgent
from graph.state import AgentOutput
from runtime.memory_schemas import ProposalMemory, CritiqueMemory, SynthesizerMemory, EpisodicMemory

class SynthesizerReward:
    @staticmethod
    def compute(decision):
        return {
            "novelty": 0.6,
            "confidence": 0.95,
            "quality": 0.9,
            "risk_score": 0.2,
            "reason": "synthesized winner selection"
        }

class SynthesizerAgent(BaseAgent):
    """
    Synthesizer Agent:
    - Combines outputs from Optimistic and Critic
    - Produces a final recommendation
    - Always outputs JSON
    """
    role = "synthesizer"

    def __init__(self, role: str, template_path: str, schema_path: str, llm: str, output_mode: str):
        super().__init__(role="synthesizer", llm=llm, template_path=template_path,
                         schema_path=schema_path, output_mode=output_mode)

    async def _process(self, state):

        print("DEBUG SYNTHESIZER state['history_agents']:", state.get("history_agents"))

        # Fetch both optimistic and critic outputs
        optimistic_memories = await self.fetch_memory(
            session_id=state["session_id"],   
            task=state["task"],
            agent="optimistic",
        )
    
        critic_memories = await self.fetch_memory(
            session_id=state["session_id"],   
            task=state["task"],
            agent="critic",
        )

        # Pull semantic summaries for this session
        episodic_memories = await self.fetch_memory(
            session_id=state["session_id"],
            agent="episodic"
        )


        optimistic_input_context = [ProposalMemory.model_validate(m).output for m in optimistic_memories]
        critic_input_context = [CritiqueMemory.model_validate(m).output for m in critic_memories]

        # Combine outputs into input_context
        combined_input_context = {
            "optimistic": optimistic_input_context,
            "critic": critic_input_context,
        }

        # Build prompt sections for each category
        episodic_sections = []
        for mem in episodic_memories:
            validated = EpisodicMemory.model_validate(mem)
            section = f"[EPISODIC MEMORY: {validated.category}]\n{validated.summary}"
            episodic_sections.append(section)

        episodic_context = "\n\n".join(episodic_sections)

        # conversation_history = ""

        print("I am in synthesizer AGENT code ..........................................")
        print("This is the conversation_history **********************")
        print(combined_input_context)


        prompt = self.build_prompt(state["task"], 
            context=str(combined_input_context),
            category = "intent",
            episodic_summary = episodic_context)

        print(prompt)
        
        output_str = await self.generate(prompt)
        output_json = None

        if self.output_mode == "json":
            try:
                output_json = self.parse_llm_json(output_str)
                await self.validate_output(output_json)
            except Exception as e:
                # Emit event instead of raising to prevent stage blocking
                await self._emit(
                    "agent_error",
                    {"agent": self.role, "stage": state["stage"], "error": str(e)}
                )
                # fallback to empty structured output
                output_json = {}

        # Use the JSON output if available
        output = output_json if output_json is not None else output_str

        print("DEBUG synthesizer AgentOutput:", AgentOutput(
            stage=state["stage"],
            role=self.role,
            output=output,
        ))

        # Persist output to cross-stage memory
        # Store memory
        await self.store_memory(
            SynthesizerMemory(
                session_id=state["session_id"],
                task=state["task"],
                agent="synthesizer",
                stage=state["stage"],
                input_context=combined_input_context,
                decision=output
            )
        )

        # Emit reward
        reward = SynthesizerReward.compute(output)

        # Evaluate if we need to compact and prune memory
        # this gets executed in the runtime
        # runtime.episodic_memory_manager has subcribed to evaluate_memory event
        await self.event_bus.emit("evaluate_episodic_memory", {
            "session_id": state["session_id"],
            "task": state["task"],
            "stage": state["stage"]  # may get ignored, and "summary" is used as stage
        })


        await self._emit("reward_assigned", {"agent": self.role, "reward": reward})



        return output 
