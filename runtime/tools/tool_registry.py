from __future__ import annotations
import importlib
import json
from pathlib import Path
from typing import Dict

from runtime.tools.base import Tool
from runtime.logger import AgentLogger


class ToolRegistry:
    """
    Platform-level registry of all tools.
    Loaded ONCE at PlatformRuntime initialization.
    """

    def __init__(self, platform_tools_path: Path):

        self.platform_tools_path = platform_tools_path
        self._tools: Dict[str, Tool] = {}

        # Bind workspace logger ONCE
        global logger
        logger = AgentLogger.get_logger(None, component="system")

    def load(self):
        logger.info("Loading platform tools")
        data = json.loads(self.platform_tools_path.read_text())

        for tool_def in data["tools"]:
            tool = self._load_tool(tool_def)
            self._tools[tool_def["name"]] = tool
            logger.info(f"Registered tool: {tool_def['name']}")

    def _load_tool(self, tool_def: dict) -> Tool:
        module_path, class_name = tool_def["entrypoint"].rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls(tool_def)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

