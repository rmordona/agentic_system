from dataclasses import dataclass, field

@dataclass(frozen=True)
class RoundRecord:
    outputs: dict

@dataclass
class Memory:
    task: str
    rounds: list = field(default_factory=list)

    def add_round(self, outputs):
        self.rounds.append(RoundRecord(outputs))

    def render_history(self):
        text = ""
        for i, r in enumerate(self.rounds, 1):
            text += f"\nROUND {i}\n"
            for agent, output in r.outputs.items():
                text += f"{agent.upper()}:\n{output}\n"
        return text.strip()

