from mcp.server.fastmcp import FastMCP

# Initialize the server instance
# This creates the 'mcp' object that your decorator is looking for
mcp = FastMCP("HumanApprovalService")

@mcp.tool()
async def request_human_approval(reason: str, options: list[str]):
    """
    Suspends execution to wait for a human decision.
    Used for high-value transactions or ambiguous data.
    """
    # This tool is a 'stub'. The CoreEngine recognizes this name 
    # and triggers a LangGraph Interrupt.
    return {"status": "PENDING_HUMAN", "reason": reason}
