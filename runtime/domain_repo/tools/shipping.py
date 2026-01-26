from mcp.server.fastmcp import FastMCP

# Initialize the server instance
# This creates the 'mcp' object that your decorator is looking for
mcp = FastMCP("Calculate Shippin")

@mcp.tool()
async def calculate_shipping(weight: float, zip_code: str):
    """Calculates shipping cost based on weight and destination."""
    # Pure atomic logic
    rate = 5.0 + (weight * 0.5)
    return {"cost": rate, "carrier": "FedEx"}
