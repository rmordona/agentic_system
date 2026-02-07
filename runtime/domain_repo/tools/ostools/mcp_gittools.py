import os
import subprocess
import json
import shutil
import hashlib
import time
from typing import List, Optional, Literal
from fastmcp import FastMCP

# 1. Initialize Server with high-level context for the LLM
mcp = FastMCP(
    "DevOS-Toolkit-Pro",
    instructions="A production-ready suite of OS and Git tools for software development automation."
)

# --- CATEGORY: FILESYSTEM ---

@mcp.tool()
def list_directory_tree(path: str, max_depth: int = 3) -> str:
    """Recursively lists files. Use to understand project structure before editing."""
    try:
        cmd = ["tree", "-L", str(max_depth), path] if shutil.which("tree") else ["ls", "-R", path]
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def read_file_with_lines(file_path: str) -> str:
    """Reads file with line numbers. Required for precision refactoring."""
    try:
        with open(file_path, 'r') as f:
            return "".join([f"{i+1}: {line}" for i, line in enumerate(f)])
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_codebase_grep(query: str, path: str = ".") -> str:
    """Regex search to find definitions or TODOs. Use when file structure is unknown."""
    return subprocess.check_output(["grep", "-rnE", query, path], text=True)

@mcp.tool()
def get_file_metadata(file_path: str) -> str:
    """Returns size, permissions, and modification time."""
    stats = os.stat(file_path)
    return f"Size: {stats.st_size}b, Perms: {oct(stats.st_mode)}, Modified: {stats.st_mtime}"

@mcp.tool()
def atomic_write_file(file_path: str, content: str) -> str:
    """Writes content safely via a temp file. Use for all code modifications."""
    temp_path = f"{file_path}.tmp"
    with open(temp_path, 'w') as f:
        f.write(content)
    os.replace(temp_path, file_path)
    return f"Successfully wrote to {file_path}"

# --- CATEGORY: GIT ---

@mcp.tool()
def git_status_summary() -> str:
    """Returns summarized git status. Check this before staging or committing."""
    return subprocess.check_output(["git", "status", "-s"], text=True)

@mcp.tool()
def git_diff_staged() -> str:
    """Returns diff of staged changes. Use for self-review before commit."""
    return subprocess.check_output(["git", "diff", "--staged"], text=True)

@mcp.tool()
def git_create_branch(branch_name: str) -> str:
    """Creates and switches to a new branch."""
    return subprocess.check_output(["git", "checkout", "-b", branch_name], text=True)

@mcp.tool()
def git_commit_with_message(message: str) -> str:
    """Commits staged changes. Requires a descriptive message."""
    return subprocess.check_output(["git", "commit", "-m", message], text=True)

@mcp.tool()
def git_log_recent(count: int = 5) -> str:
    """Returns last N commit messages and hashes."""
    return subprocess.check_output(["git", "log", "--oneline", "-n", str(count)], text=True)

# --- CATEGORY: PROCESS & SYSTEM ---

@mcp.tool()
def execute_shell_command(command: str, timeout_seconds: int = 30) -> str:
    """Runs restricted shell commands (e.g., npm test). SECURITY: Requires HITL approval."""
    return subprocess.check_output(command, shell=True, text=True, timeout=timeout_seconds)

@mcp.tool()
def get_environment_variables(filter_prefix: Optional[str] = None) -> str:
    """Lists env variables (scrubs 'KEY', 'SECRET', 'TOKEN'). Use for config debugging."""
    envs = {k: v for k, v in os.environ.items() if not any(s in k.lower() for s in ["key", "secret", "token"])}
    if filter_prefix:
        envs = {k: v for k, v in envs.items() if k.startswith(filter_prefix)}
    return json.dumps(envs, indent=2)

@mcp.tool()
def check_port_availability(port: int) -> str:
    """Checks if a port is in use before starting local servers."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return "In Use" if s.connect_ex(('localhost', port)) == 0 else "Available"

@mcp.tool()
def list_running_processes(search_term: str) -> str:
    """Lists processes by name (e.g., 'python', 'node')."""
    return subprocess.check_output(["pgrep", "-fl", search_term], text=True)

@mcp.tool()
def kill_process_by_port(port: int) -> str:
    """Kills process on a port. Use if a dev server hangs."""
    try:
        pid = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True).strip()
        os.kill(int(pid), 9)
        return f"Killed process {pid} on port {port}"
    except:
        return "No process found on port."

# --- CATEGORY: UTILITIES ---

@mcp.tool()
def parse_json_safe(json_string: str) -> str:
    """Validates and pretty-prints JSON."""
    return json.dumps(json.loads(json_string), indent=2)

@mcp.tool()
def convert_timestamp(value: str, target: Literal["UNIX", "ISO"]) -> str:
    """Converts time formats for log analysis."""
    from datetime import datetime
    if target == "ISO":
        return datetime.fromtimestamp(float(value)).isoformat()
    return str(time.mktime(datetime.fromisoformat(value).timetuple()))

@mcp.tool()
def extract_archive(file_path: str, destination: str) -> str:
    """Unpacks zip/tar files into a directory."""
    shutil.unpack_archive(file_path, destination)
    return f"Extracted to {destination}"

@mcp.tool()
def calculate_file_hash(file_path: str) -> str:
    """Returns SHA-256 hash for integrity checks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""): h.update(chunk)
    return h.hexdigest()

@mcp.tool()
def inspect_docker_container(container_name: str) -> str:
    """Returns metadata/logs for a Docker container."""
    return subprocess.check_output(["docker", "inspect", container_name], text=True)

if __name__ == "__main__":
    # mcp.run() defaults to STDIO transport
    mcp.run()
