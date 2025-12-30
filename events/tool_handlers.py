from tools.mcp_client import mcp_client

INTENT_TO_TOOL = {
    "check_availability": "search_availability",
}

def register_tool_handlers(event_bus):

    @event_bus.on("tool_call")
    async def handle_tool_call(event):
        agent = event["agent"]
        intent = event["intent"]
        stage = event["stage"]
        payload = event["query"]

        tool = INTENT_TO_TOOL.get(intent)
        if not tool:
            raise RuntimeError(f"Unknown intent: {intent}")

        result = await mcp_client.call(tool, payload)

        await event_bus.emit(
            "tool_result",
            {
                "tool": tool,
                "stage": stage,
                "result": result,
            }
        )

