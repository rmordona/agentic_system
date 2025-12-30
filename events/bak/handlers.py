from tools.runtime import execute_with_retry
from tools.booking_tools import search_availability

INTENT_TO_TOOL = {
    "check_availability": "search_availability",
}

def register_tool_handlers(event_bus):

    @event_bus.on("tool_call")
    async def handle_tool_call(event):
        tool = event["tool"]
        payload = event.get("query")
        stage = event.get("stage")

        try:
            if tool == "search_availability":
                result = await execute_with_retry(
                    search_availability,
                    payload,
                    retries=3,
                )

            await event_bus.emit(
                "tool_result",
                {
                    "tool": tool,
                    "stage": stage,
                    "result": result,
                }
            )

        except Exception as e:
            # Compensation event
            await event_bus.emit(
                "tool_failed",
                {
                    "tool": tool,
                    "error": str(e),
                    "stage": stage,
                }
            )


    @event_bus.on("tool_result")
    async def route_tool_result(event):
        stage = event["stage"]

        if stage != "booking":
            return  # Ignore result safely

        await event_bus.emit(
            "state_patch",
            {
                "history": [{
                    "role": "tool",
                    "output": event["result"]
                }]
            }
        )


    @event_bus.on("tool_call")
    async def resolve_intent(event):
        intent = event["intent"]
        tool = INTENT_TO_TOOL.get(intent)

        if not tool:
            raise RuntimeError(f"Unknown intent: {intent}")

        event["tool"] = tool

