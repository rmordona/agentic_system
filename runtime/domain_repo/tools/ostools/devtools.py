import asyncio
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("LinuxDevTools")

# -------------------------------------------------------------------
# Generic CLI wrapper
# -------------------------------------------------------------------
async def _run_cli(command: str, args: list[str] = []):
    """
    Execute a CLI command asynchronously and return structured output.
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

# -------------------------------------------------------------------
# File & Directory Tools
# -------------------------------------------------------------------
@mcp.tool()
async def list_dir(path: str = "."):
    """List files in a directory with details."""
    return await _run_cli("ls", ["-la", path])

@mcp.tool()
async def find_files(path: str = ".", pattern: str = "*"):
    """Find files matching a pattern under a directory."""
    return await _run_cli("find", [path, "-name", pattern])

@mcp.tool()
async def disk_usage(path: str = "."):
    """Check disk usage for a directory."""
    return await _run_cli("du", ["-sh", path])

@mcp.tool()
async def disk_free():
    """Check free disk space on all mounted filesystems."""
    return await _run_cli("df", ["-h"])

# -------------------------------------------------------------------
# Text & Data Processing Tools
# -------------------------------------------------------------------
@mcp.tool()
async def grep_text(pattern: str, file_path: str):
    """Search for a pattern in a file."""
    return await _run_cli("grep", ["-n", pattern, file_path])

@mcp.tool()
async def awk_process(script: str, file_path: str):
    """Process a file using awk."""
    return await _run_cli("awk", [script, file_path])

@mcp.tool()
async def sed_replace(script: str, file_path: str):
    """Apply a sed transformation to a file."""
    return await _run_cli("sed", [script, file_path])

@mcp.tool()
async def jq_filter(json_path: str, filter_expr: str):
    """Filter a JSON file using jq."""
    return await _run_cli("jq", [filter_expr, json_path])

# -------------------------------------------------------------------
# Git & Version Control
# -------------------------------------------------------------------
@mcp.tool()
async def git_status(repo_path: str = "."):
    """Get git status of a repository."""
    return await _run_cli("git", ["-C", repo_path, "status", "--porcelain"])

@mcp.tool()
async def git_log(repo_path: str = ".", max_entries: int = 5):
    """Get the latest git commits."""
    return await _run_cli("git", ["-C", repo_path, "log", f"-n{max_entries}"])

# -------------------------------------------------------------------
# Networking & API
# -------------------------------------------------------------------
@mcp.tool()
async def curl_request(url: str, method: str = "GET"):
    """Perform an HTTP request with curl."""
    return await _run_cli("curl", ["-s", "-X", method, url])

@mcp.tool()
async def ping_host(host: str, count: int = 4):
    """Ping a host to check connectivity."""
    return await _run_cli("ping", ["-c", str(count), host])

# -------------------------------------------------------------------
# Docker / Containers
# -------------------------------------------------------------------
@mcp.tool()
async def docker_ps():
    """List running Docker containers."""
    return await _run_cli("docker", ["ps"])

@mcp.tool()
async def docker_images():
    """List Docker images."""
    return await _run_cli("docker", ["images"])

# -------------------------------------------------------------------
# Human-in-the-loop / Control Tools
# -------------------------------------------------------------------
@mcp.tool()
async def request_human_approval(reason: str, options: list[str]):
    """
    Suspend execution and request human decision.
    Used for ambiguous tasks or high-value actions.
    """
    return {"status": "PENDING_HUMAN", "reason": reason, "options": options}

