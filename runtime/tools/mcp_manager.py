import os
import importlib.util
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession

class MCPManager:
    def __init__(self, tools_dir="./tools"):
        self.tools_dir = tools_dir
        self.sessions = {}
        self.server_params = {}

    def discover_servers(self):
        """Scans the tools directory for Python files and maps them as MCP servers."""
        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                server_name = filename[:-3]  # Remove .py
                file_path = os.path.join(self.tools_dir, filename)
                
                # Assign parameters for Stdio transport
                # We assume each file is a self-contained FastMCP server
                self.server_params[server_name] = StdioServerParameters(
                    command="python",
                    args=[file_path]
                )
                print(f"🔎 Discovered tool module: {server_name}")

    async def start_all(self):
        """Connects to every discovered server."""
        for name, params in self.server_params.items():
            try:
                transport = await stdio_client(params)
                read, write = transport
                session = ClientSession(read, write)
                await session.initialize()
                self.sessions[name] = session
                print(f"🚀 Started MCP Session: {name}")
            except Exception as e:
                print(f"❌ Failed to start {name}: {e}")

    async def get_all_available_tools(self, allowed_names: list):
        """Fetches tool definitions across all sessions filtering by allowed list."""
        valid_tools = []
        for session in self.sessions.values():
            result = await session.list_tools()
            for tool in result.tools:
                if tool.name in allowed_names:
                    valid_tools.append(tool)
        return valid_tools
