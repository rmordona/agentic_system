# -----------------------------------------------------------------------------
# Project: Agentic System
# File: runtime/tools/tool_registry.py
#
# Description:
#   ToolRegistry is the centralized discovery, registration, and access layer
#   for executable tools within the agentic system.
#
#   It provides a unified abstraction over:
#     1. Local Python-based tools (static, in-repo capabilities)
#     2. Remote MCP / FastMCP tools (external processes, dynamic capabilities)
#
#   The registry itself is intentionally:
#     - Agent-agnostic
#     - Pipeline-agnostic
#     - Policy-unaware
#
#   It does NOT decide:
#     - Which agent may use a tool
#     - When a tool should be invoked
#     - Whether a tool invocation is safe or correct
#
#   Those decisions belong strictly to:
#     AGENT.md  → agent.json  → Orchestrator / Policy Layer
#
#   ToolRegistry ONLY answers:
#     “If authorized, how do I call this capability?”
#
# Responsibilities:
#   - Discover and register local Python tools via filesystem scanning
#   - Dynamically import tool modules safely and deterministically
#   - Connect to MCP-compatible external tool servers over stdio
#   - Wrap remote tools into local callable interfaces
#   - Provide lookup and enumeration of available tools
#
# Design Principles:
#   - Zero business logic
#   - Zero agent-specific assumptions
#   - Late binding of capabilities
#   - Explicit registration, no implicit execution
#   - Observable behavior via structured logging
#
# Production Notes:
#   - Tool discovery happens at startup
#   - MCP sessions are long-lived per connection
#   - Lifecycle management of MCP servers should be handled externally
#   - All registration events are logged for auditability
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# -----------------------------------------------------------------------------

import importlib.util
import inspect
import os
from pathlib import Path
from typing import Any, Dict, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class ToolRegistry:
    """
    Central registry for executable tools.

    Supports:
      - Local Python functions (runtime/tools/*.py)
      - Remote MCP / FastMCP tools over stdio

    This class is intentionally unaware of agents, skills, or policies.
    """

    def __init__(self, tools_dir: str = "runtime/tools"):
        self.tools_dir = Path(tools_dir)
        self._tools: Dict[str, Callable] = {}
        self._mcp_clients: Dict[str, Any] = {}

        logger.info(
            "Initializing ToolRegistry",
            extra={"tools_dir": str(self.tools_dir)}
        )

        # Initialize the registry by scanning the folder
        self._discover_local_tools()

        logger.info(
            "ToolRegistry initialization complete",
            extra={"registered_tools": list(self._tools.keys())}
        )

        def get_tools_for_context(self, context: SessionContext):
            """
            The 'Librarian' logic: Matches tools to the current reality.
            """
            # 1. Determine the domain from the current stage in artifact.md
            current_domain = context.metadata.get("domain", "general")
            
            # 2. Identify the shape of the data plane (e.g., 'JSON', 'Python', 'CSV')
            body_type = context.data_type

            # 3. Filter the registry for tools that match BOTH
            available_tools = self.registry.filter(
                domain=current_domain,
                compatible_body=body_type
            )
            
            return available_tools


    # -------------------------------------------------------------------------
    # Local Tool Discovery
    # -------------------------------------------------------------------------

    def _discover_local_tools(self):
        """Scans the tools folder and imports valid Python functions."""
        if not self.tools_dir.exists():
            logger.warning(
                "Tools directory does not exist; creating",
                extra={"path": str(self.tools_dir)}
            )
            os.makedirs(self.tools_dir)
            return

        logger.info(
            "Discovering local tools",
            extra={"path": str(self.tools_dir)}
        )

        for file_path in self.tools_dir.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            module_name = file_path.stem
            self._import_from_file(module_name, file_path)

    def _import_from_file(self, module_name: str, file_path: Path):
        """Dynamic import using importlib."""
        logger.debug(
            "Importing tool module",
            extra={"module": module_name, "path": str(file_path)}
        )

        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Register functions that are intended to be tools
            # Criteria:
            #   - Not private
            #   - Has a docstring (explicit intent)
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("_") and obj.__doc__:
                    tool_name = name
                    self._tools[tool_name] = obj
                    logger.info(
                        "Registered local tool",
                        extra={"tool": tool_name}
                    )

    # -------------------------------------------------------------------------
    # MCP / Remote Tool Support
    # -------------------------------------------------------------------------

    async def connect_mcp_server(self, name: str, command: str, args: list):
        """
        Connects to an MCP / FastMCP server and registers its tools.

        NOTE:
        - Lifecycle management of the server process is out of scope.
        - This method assumes the server adheres to MCP protocol.
        """
        logger.info(
            "Connecting to MCP server",
            extra={"name": name, "command": command, "args": args}
        )

        server_params = StdioServerParameters(command=command, args=args)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                logger.info(
                    "Discovered MCP tools",
                    extra={"server": name, "tool_count": len(tools)}
                )

                for tool in tools:
                    self._tools[tool.name] = self._make_mcp_wrapper(session, tool.name)
                    logger.info(
                        "Registered MCP tool",
                        extra={"tool": tool.name, "server": name}
                    )

    def _make_mcp_wrapper(self, session, tool_name):
        """Creates a callable wrapper for remote MCP tools."""
        async def wrapper(**kwargs):
            logger.debug(
                "Invoking MCP tool",
                extra={"tool": tool_name, "arguments": kwargs}
            )
            return await session.call_tool(tool_name, arguments=kwargs)
        return wrapper

    # -------------------------------------------------------------------------
    # Public Accessors
    # -------------------------------------------------------------------------

    def get_tool(self, tool_name: str) -> Callable:
        """Retrieve a tool by name."""
        if tool_name not in self._tools:
            logger.error(
                "Requested tool not found",
                extra={"tool": tool_name}
            )
            raise KeyError(f"Tool '{tool_name}' not found in registry.")

        logger.debug(
            "Tool retrieved",
            extra={"tool": tool_name}
        )
        return self._tools[tool_name]

    def list_available_tools(self) -> list:
        """List all registered tool names."""
        return list(self._tools.keys())


# --- Usage Example ---
# registry = ToolRegistry()
# search_tool = registry.get_tool("web_search")
