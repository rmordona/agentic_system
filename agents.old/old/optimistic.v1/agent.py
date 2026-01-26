import json
from agents.base import BaseAgent
from graph.state import AgentOutput
from runtime.memory_schemas import ProposalMemory

class OptimisticReward:
    @staticmethod
    def compute(proposal: dict) -> dict:
        """
        Compute reward for an optimistic proposal.

        Assumes proposal conforms to:
        - title: str
        - core_ideas: list[str]
        - key_features: list[str]
        - win_rationale: list[str]
        """

        core_ideas = proposal.get("core_ideas", [])
        key_features = proposal.get("key_features", [])
        win_rationale = proposal.get("win_rationale", [])

        print("core_ideas")

        # ---- Novelty: breadth of ideas and features
        # Normalize so 5 items ~= full score
        novelty = min(
            (len(core_ideas) + len(key_features)) / 8,
            1.0
        )

        # ---- Quality: completeness of structure
        quality = (
            0.4 * (1 if core_ideas else 0) +
            0.4 * (1 if key_features else 0) +
            0.2 * (1 if win_rationale else 0)
        )

        # ---- Confidence: optimistic bias
        confidence = 0.8

        # ---- Risk: fewer rationales = higher risk
        risk_score = max(0.1, 0.5 - 0.1 * len(win_rationale))

        return {
            "novelty": round(novelty, 2),
            "confidence": confidence,
            "quality": round(quality, 2),
            "risk_score": round(risk_score, 2),
            "reason": "Optimistic ideation based on breadth of ideas and features"
        }


class OptimisticAgent(BaseAgent):
    """
    Optimistic Agent:
    - Explores solution space aggressively
    - Outputs ambitious, high-upside ideas
    - JSON output mode suitable for schema compliance
    """

    role = "optimistic"

    def __init__(self, role: str, template_path: str, schema_path: str, llm: str, output_mode: str):
        super().__init__("optimistic", llm = llm, template_path=template_path, schema_path=schema_path,   output_mode=output_mode)

    async def _process(self, state):
        # Fetch memory from both Optimistic agents
        memories = await self.fetch_memory(
            session_id=state["session_id"],   
            task=state["task"],
            agent="optimistic",
        )

        input_context = [ProposalMemory.model_validate(m).output for m in memories]

        prompt = self.build_prompt(state["task"], context=str(input_context))

        print("I am in optimistic AGENT code ..........................................")
        print(prompt)

        output_str = await self.generate(prompt)
        output_json = None

        print("[OUTPUT OPTIMIST]")
        print(self.output_mode)
        print("*****")
        print(output_str)
        print("*****")
        if self.output_mode == "json":
            try:
                output_json = self.parse_llm_json(output_str)
                await self.validate_output(output_json)
            except Exception as e:
                raise ValueError(f"Optimistic Agent {self.role} produced invalid JSON output: {e}")

        # Determine what to emit
        output = output_json if output_json is not None else output_str

        await self.call_tool("log_proposals", {"proposals": output, "state": state })


        print("DEBUG optimistic AgentOutput:", AgentOutput(
            stage=state["stage"],
            role=self.role,
            output=output,
        ))

        # Store memory
        await self.store_memory(
            ProposalMemory(
                session_id=state["session_id"],   
                task=state["task"],
                agent="optimistic",
                stage=state["stage"],
                input_context=input_context,  # optional, what the agent saw
                output=output
            )
        )


        reward = OptimisticReward.compute(output)

        await self._emit("reward_assigned", {"agent": self.role, "reward": reward})

        print("optimistic (_process) Going to return agents now ...")

        return output 
