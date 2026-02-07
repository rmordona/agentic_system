import asyncio
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LinuxDevTools")

# Generic wrapper for CLI tools
@mcp.tool()
async def run_cli_tool(command: str, args: list[str] = []):
    """
    Executes a Linux CLI command asynchronously and returns structured output.

    Args:
        command: The CLI command to run (e.g., 'ls', 'grep').
        args: List of arguments for the command.

    Returns:
        dict: {
            "stdout": str,
            "stderr": str,
            "return_code": int
        }
    """
    proc = await asyncio.create_subprocess_exec(
        command, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    return {
        "stdout": stdout.decode("utf-8").strip(),
        "stderr": stderr.decode("utf-8").strip(),
        "return_code": proc.returncode
    }

