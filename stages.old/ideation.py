from stages.base_stage import Stage

class IdeationStage(Stage):
    name = "ideation"
    allowed_agents = ["optimist", "critic"]

    def routing_policy(self, state, registry):
        if "optimist" not in state["rewards"]:
            return "optimist"
        if "critic" not in state["rewards"]:
            return "critic"
        return None

    def should_exit(self, state):
        return len(state["history"]) >= 4

