import json
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    url = "http://127.0.0.1:8080/mcp"  # your server’s MCP endpoint

    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Get the list of tools
            tools_list = await session.list_tools()

            tools_info = {}

            for tool in tools_list.tools:
                # Get the original Python function for introspection
                func = getattr(tool, "func", None)
                params = []

                if func is not None:
                    sig = inspect.signature(func)
                    for name, param in sig.parameters.items():
                        params.append({
                            "name": name,
                            "type": str(param.annotation) if param.annotation != inspect._empty else "Any",
                            "default": param.default if param.default != inspect._empty else None
                        })

                tools_info[tool.name] = {
                    "description": getattr(tool, "description", ""),
                    "parameters": params
                }

            # Print as formatted JSON
            print(json.dumps(tools_info, indent=2))

            # Call a tool:
            result = await session.call_tool(
                "book_flight",
                {
                    "from_airport": "SFO",
                    "to_airport": "JFK",
                    "date": "2026-03-01",
                    "passenger_name": "John Doe"
                }
            )

            print("Tool result:", result)

asyncio.run(main())

