# mcp_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Agentic MCP Server")

# ------------------------
# Tool registry
# ------------------------
TOOL_REGISTRY: Dict[str, callable] = {}

def register_tool(name: str):
    """Decorator to register a tool"""
    def decorator(func):
        TOOL_REGISTRY[name] = func
        return func
    return decorator

# Example tool
@register_tool("book_flight")
async def book_flight(args: Dict[str, Any]) -> Dict[str, Any]:
    # Simulate flight booking
    return {"confirmation": "ABC123", "details": args}

@register_tool("send_email")
async def send_email(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "sent", "to": args.get("to")}

# ------------------------
# Request model
# ------------------------
class ToolRequest(BaseModel):
    payload: Dict[str, Any]

# ------------------------
# Endpoint
# ------------------------
@app.post("/tool/{tool_name}")
async def run_tool(tool_name: str, request: ToolRequest):
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    result = await tool(request.payload)
    return result

# ------------------------
# Run server
# ------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

