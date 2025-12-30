def register_lifecycle_handlers(event_bus):

    @event_bus.on("agent_start")
    async def on_agent_start(event):
        await event_bus.emit(
            "state_patch",
            {
                "history": [{
                    "role": "system",
                    "output": f"Agent {event['agent']} started"
                }]
            }
        )

    @event_bus.on("agent_done")
    async def on_agent_done(event):
        await event_bus.emit(
            "state_patch",
            {
                "history": [{
                    "role": event["agent"],
                    "output": event["output"],
                }]
            }
        )

