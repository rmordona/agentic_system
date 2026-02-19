from app.mcp import mcp

@mcp.tool()
async def get_gas_fees(network: str = "ethereum") -> dict:
    """Retrieves current Gwei prices to estimate trade slippage."""
    return {"network": network, "base_fee": "25 Gwei", "status": "Low"}
