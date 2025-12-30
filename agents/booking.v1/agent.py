import json
from agents.base import BaseAgent

class BookingReward:
    @staticmethod
    def compute(booking_confirmation):
        return {
            "novelty": 0.4,
            "confidence": 0.95,
            "quality": 0.9,
            "risk_score": 0.1,
            "reason": "successful booking execution"
        }

class BookingAgent(BaseAgent):
    role = "booking"

    async def _process(self, state):
        # Get last output (Synthesizer) for booking
        synth_output = state.get("history", [])[-1]["output"] if state.get("history") else {}
        booking_data = synth_output.get("decision_data") or {}

        # Example tool call (replace with real booking logic)
        await self._emit(
            "tool_call",
            {
                "agent": self.role,
                "stage": state["stage"],
                "intent": "check_availability",
                "query": booking_data,
            }
        )

        # Mark agent as executed
        state.setdefault("history_agents", []).append(self.role)

        # Store output in history
        state.setdefault("history", []).append({
            "role": self.role,
            "output": {"booking_confirmation": booking_data}
        })

        # Compute reward
        reward = BookingReward.compute(booking_data)
        state.setdefault("rewards", {})[self.role] = reward
        await self._emit("reward_assigned", {"agent": self.role, "reward": reward})

        return {"booking_confirmation": booking_data}
