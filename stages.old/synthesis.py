from stages.base_stage import Stage

class SynthesisStage(Stage):
    name = "synthesis"
    allowed_agents = ["synthesizer"]

    def routing_policy(self, state, registry):
        return "synthesizer"

    def should_exit(self, state):
        return state.get("done", False)

