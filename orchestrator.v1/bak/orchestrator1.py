from dataclasses import dataclass, field
from typing import List, Dict, Any

MAX_ROUNDS = 5
MIN_AVG_SCORE_TO_WIN = 8.0

@dataclass
class RoundRecord:
    optimistic: Dict[str, Any]
    critic: Dict[str, Any]
    synthesizer: Dict[str, Any]

@dataclass
class OrchestratorState:
    task: str
    rounds: List[RoundRecord] = field(default_factory=list)
    winner_declared: bool = False

class Orchestrator:

    def __init__(self, llm):
        self.llm = llm  # abstract LLM interface

    def compose_prompt(self, system_prompt, task, history, role_instruction):
        history_text = ""
        for i, r in enumerate(history, 1):
            history_text += f"""
Round {i}:
Optimistic: {r.optimistic}
Critic: {r.critic}
Synthesizer: {r.synthesizer}
"""
        return f"""
SYSTEM:
{system_prompt}

TASK:
{task}

CONVERSATION HISTORY:
{history_text}

INSTRUCTIONS:
{role_instruction}
"""

    def run(self, task: str):
        state = OrchestratorState(task=task)

        for round_idx in range(MAX_ROUNDS):
            optimistic = self.llm.run("optimistic", state)
            critic = self.llm.run("critic", state)
            synthesizer = self.llm.run("synthesizer", state)

            state.rounds.append(
                RoundRecord(optimistic, critic, synthesizer)
            )

            if synthesizer["decision"] == "winner":
                state.winner_declared = True
                break

        return state

