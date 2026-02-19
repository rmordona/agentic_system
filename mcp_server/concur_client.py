import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def call_tool(n):
    async with streamablehttp_client("http://127.0.0.1:8080/mcp") as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            res = await session.call_tool("book_flight", {
                "from_airport": "SFO",
                "to_airport": "JFK",
                "date": "2026-03-01",
                "passenger_name": f"Passenger {n}"
            })
            print(res)

async def main():
    await asyncio.gather(*(call_tool(i) for i in range(10)))

asyncio.run(main())

