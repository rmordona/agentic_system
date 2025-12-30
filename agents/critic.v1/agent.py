import json
from agents.base import BaseAgent
from graph.state import AgentOutput
from runtime.memory_schemas import CritiqueMemory

class CriticReward:
    @staticmethod
    def compute(proposal: dict) -> dict:
        """
        Compute reward for a critic evaluation of a proposal.

        Assumes proposal conforms to:
        - major_risks: list[str]
        - unrealistic_assumptions: list[str]
        - failure_scenarios: list[str]
        - required_changes: list[str]

        The scores are adjusted to reflect a critical perspective:
        - Novelty: penalize if too conventional
        - Quality: completeness of risk assessment
        - Confidence: moderate (not optimistic)
        - Risk_score: higher if major risks are identified
        """

        major_risks = proposal.get("major_risks", [])
        unrealistic_assumptions = proposal.get("unrealistic_assumptions", [])
        failure_scenarios = proposal.get("failure_scenarios", [])
        required_changes = proposal.get("required_changes", [])

        # ---- Novelty: if fewer assumptions, more novel
        novelty = max(0.0, 1.0 - len(unrealistic_assumptions) / 5)

        # ---- Quality: thoroughness of risk analysis
        quality = (
            0.4 * (1 if major_risks else 0) +
            0.3 * (1 if failure_scenarios else 0) +
            0.2 * (1 if unrealistic_assumptions else 0) +
            0.1 * (1 if required_changes else 0)
        )

        # ---- Confidence: moderate, critic is cautious
        confidence = 0.6

        # ---- Risk: more identified risks → higher risk score
        risk_score = min(1.0, 0.1 + 0.2 * len(major_risks))

        return {
            "novelty": round(novelty, 2),
            "confidence": confidence,
            "quality": round(quality, 2),
            "risk_score": round(risk_score, 2),
            "reason": "Critical evaluation focusing on realism and risk mitigation"
        }


class CriticAgent(BaseAgent):
    """
    Critic Agent:
    - Evaluates risks, weaknesses, or inconsistencies
    - Output can be text-based reasoning or JSON
    """
    role = "critic"

    def __init__(self, role: str, template_path: str, schema_path: str, llm: str, output_mode: str):
        super().__init__(role="critic", llm = llm, template_path=template_path, schema_path=schema_path,   output_mode=output_mode)



    async def _process(self, state):
        # from all stages

        print("DEBUG CRITIC state['history_agents']:", state.get("history_agents"))

        # Get optimistic memory for context
        memories = await self.fetch_memory(
            session_id=state["session_id"],   
            task=state["task"],
            agent="optimistic",
        )

        input_context = [CritiqueMemory.model_validate(m).output for m in memories]


        conversation_history = ""

        print("This is the conversation_history **********************")
        print(input_context)
    
        prompt = self.build_prompt(state["task"], context = str(input_context))

        print("I am in critic AGENT code ..........................................")
        print("[HISTORY]:", conversation_history)
        print(prompt)

        output_str = await self.generate(prompt)
        output_json = None

        print("[OUTPUT CRITIC]")
        print(self.output_mode)
        print("*****")
        print(output_str)
        print("*****")
        if self.output_mode == "json":
            try:
                output_json = self.parse_llm_json(output_str)
                await self.validate_output(output_json)
            except Exception as e:
                raise ValueError(f"Critic Agent {self.role} produced invalid JSON output: {e}")

        # Determine what to emit
        output = output_json if output_json is not None else output_str

        await self.call_tool("log_critique", {"critique": output, "state": state })

        print("DEBUG critic AgentOutput:", AgentOutput(
            stage=state["stage"],
            role=self.role,
            output=output,
        ))

        # Store memory
        await self.store_memory(
            CritiqueMemory(
                session_id=state["session_id"],
                task=state["task"],
                agent="critic",
                stage=state["stage"],
                input_context=input_context,
                output=output
            )
        )

        reward = CriticReward.compute(output)

        await self._emit("reward_assigned", {"agent": self.role, "reward": reward})


        return output 
