import random

class MockLLM:
    def generate(self, prompt):
        return {
            "summary": "Mock response/synthesis",
            "scorecard": {
                "feasibility": random.randint(7,9),
                "differentiation": random.randint(8,10),
                "user_value": random.randint(7,9),
                "risk_mitigation": random.randint(6,9),
                "consistency": random.randint(7,9)
            },
            "decision": "winner",
            "rationale": "Mock decision/converge"
        }

