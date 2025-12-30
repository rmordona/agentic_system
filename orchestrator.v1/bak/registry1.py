class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, agent):
        self.agents[agent.name] = agent

    def get_all(self):
        return self.agents

