import asyncio

async def log_tool_execution(event):
    agent = event["agent"]
    output = event["output"]

    # Check if this output contains a tool_call
    if "tool_call" in output:
        tool_call = output["tool_call"]
        print(f"[TOOL EXECUTION] Agent: {agent}")
        print(f"  Tool: {tool_call['name']}")
        print(f"  Arguments: {tool_call['arguments']}")

        # If BaseAgent executed the tool, result should be in state history
        last_history = event["state"]["history"][-1][1]
        if "confirmation_number" in last_history:
            confirmation = last_history["confirmation_number"]
            print(f"  Booking confirmed: {confirmation}\n")

