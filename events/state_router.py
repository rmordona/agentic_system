def register_state_router(event_bus):
    """
    Converts external events into LangGraph-safe state patches.
    """

    # -------------------------
    # Tool → history
    # -------------------------
    @event_bus.on("tool_result")
    async def tool_to_history(event):
        if event["stage"] != "booking":
            return

        await event_bus.emit(
            "state_patch",
            {
                "history": [{
                    "role": "tool",
                    "output": event["result"],
                }]
            }
        )

    # -------------------------
    # Tool → reward
    # -------------------------
    @event_bus.on("tool_result")
    async def tool_to_reward(event):
        if event["stage"] != "booking":
            return

        await event_bus.emit(
            "state_patch",
            {
                "rewards": {
                    event["agent"]: {
                        "novelty": 0.4,
                        "confidence": 0.95,
                        "quality": 0.9,
                        "risk_score": 0.1,
                        "reason": "successful tool execution",
                    }
                }
            }
        )
