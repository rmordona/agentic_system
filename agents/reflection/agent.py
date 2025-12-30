from agents.base import BaseAgent, RewardModel

class ReflectionReward(RewardModel):
    def score(self, output, state):
        return 0.5

class ReflectionAgent(BaseAgent):
    role = "reflection"
    def reward_model(self): return ReflectionReward()

