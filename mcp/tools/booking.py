from tools.mcp_server import mcp

@mcp.tool()
async def search_availability(
    location: str,
    start_date: str,
    end_date: str,
) -> dict:
    # Simulated external API
    return {
        "location": location,
        "available": True,
        "price": 220,
        "currency": "USD",
    }

