from __future__ import annotations

import importlib
import pkgutil
import inspect
import importlib.util
from app.mcp_instance import mcp
import app.tools  # tools package

# ------------------------
# Startup: auto-import all tools
# ------------------------
for loader, module_name, is_pkg in pkgutil.iter_modules(app.tools.__path__):
    if module_name.endswith("_tool"):
        importlib.import_module(f"app.tools.{module_name}")

# ------------------------
# Runtime tool hot-loader
# ------------------------
@mcp.tool()
async def load_tool(file_path: str):
    """
    Hot-load a new tool from a Python file at runtime.
    The file must define async functions decorated with @mcp.tool()
    and optionally _metadata for parameter info.
    """
    spec = importlib.util.spec_from_file_location("dynamic_tool", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    loaded = []
    for name, obj in inspect.getmembers(module):
        if inspect.iscoroutinefunction(obj) and hasattr(obj, "_is_mcp_tool"):
            mcp.register_tool(obj.__name__, obj)
            loaded.append(obj.__name__)
    return {"loaded_tools": loaded}

# ------------------------
# Optional: expose tool schemas
# ------------------------
@mcp.tool()
async def get_tool_schema(tool_name: str):
    """
    Get input parameters and metadata for a registered tool.
    """
    tool = mcp.tools.get(tool_name)
    if not tool:
        return {"error": f"Tool {tool_name} not found"}

    func = getattr(tool, "func", None)
    params = []
    if func:
        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            params.append({
                "name": name,
                "type": str(param.annotation) if param.annotation != inspect._empty else "Any",
                "default": param.default if param.default != inspect._empty else None
            })
    # Include custom metadata if present
    metadata = getattr(tool, "_metadata", {})

    return {"description": getattr(tool, "description", ""), "parameters": params, "metadata": metadata}

# ------------------------
# Run server
# ------------------------
if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="http", host="127.0.0.1", port=8080)
    print("Server stopped.")
