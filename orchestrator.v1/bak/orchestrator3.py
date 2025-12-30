MAX_ROUNDS = 5

class Orchestrator:
    def __init__(self, registry, memory):
        self.registry = registry
        self.memory = memory

    def run(self):
        for _ in range(MAX_ROUNDS):
            history = self.memory.render()
            outputs = {}

            for name, agent in self.registry.agents().items():
                outputs[name] = agent.run(
                    self.memory.task,
                    history
                )

	    # Add Round
            self.memory.append(outputs)

            if "synthesizer" in outputs:
                if outputs["synthesizer"]["decision"] == "winner":
                    return outputs["synthesizer"]

        return None

