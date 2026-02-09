from fastmcp import FastMCP

# Define the server
crypto_mcp = FastMCP("CryptoIntelligence")

@crypto_mcp.tool()
async def get_gas_fees(network: str = "ethereum") -> dict:
    """Retrieves current Gwei prices to estimate trade slippage."""
    return {"network": network, "base_fee": "25 Gwei", "status": "Low"}

if __name__ == "__main__":
    crypto_mcp.run()
