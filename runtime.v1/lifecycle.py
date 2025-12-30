# runtime/lifecycle.py
def register_lifecycle_handlers(event_bus):

    @event_bus.on("agent_start")
    async def on_agent_start(event):
        print(f"[AGENT START] {event['agent']}")

    @event_bus.on("agent_done")
    async def on_agent_done(event):
        print(f"[AGENT DONE] {event['agent']} → {event['output']}")

    @event_bus.on("tool_call")
    async def on_tool_call(event):
        print(f"[TOOL] {event}")

