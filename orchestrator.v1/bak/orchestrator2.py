MAX_ROUNDS = 5

class Orchestrator:
    def __init__(self, registry, memory):
        self.registry = registry
        self.memory = memory

    def run(self):
        for _ in range(MAX_ROUNDS):
            history = self.memory.render_history()
            outputs = {}

            for name, agent in self.registry.get_all().items():
                outputs[name] = agent.run(
                    self.memory.task,
                    history
                )

            self.memory.add_round(outputs)

            if "synthesizer" in outputs:
                if outputs["synthesizer"]["decision"] == "winner":
                    return outputs["synthesizer"]

        return None

