from fastmcp import FastMCP

# This name will be used by the ToolManager for registration
mcp = FastMCP("ZillowIntegration")

@mcp.tool()
async def fetch_zestimate(address: str):
    """
    Fetches the current market estimate (Zestimate) and property 
    specs for a given address.
    """
    # In a real scenario, this hits the Zillow API. 
    # For now, we return the raw 'fact bag'
    print(f"--- Calling Zillow API for: {address} ---")
    
    return {
        "estimated_value": 450000.0,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "square_footage": 1850,
        "year_built": 1995,
        "property_id": "ZIL-992834"
    }
