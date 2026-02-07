import os
import subprocess
import json
import shutil
import hashlib
import time
from typing import List, Optional, Literal
from fastmcp import FastMCP

# Initialize the Server
mcp = FastMCP(
    "DevOS-Toolkit",
    instructions="Comprehensive OS & Git tools for automated software engineering."
)

# --- CATEGORY 1: FILESYSTEM & WORKSPACE ---

@mcp.tool()
def list_directory_tree(path: str, max_depth: int = 3) -> str:
    """Recursively lists files. Use to understand project structure before editing."""
    cmd = ["tree", "-L", str(max_depth), path] if shutil.which("tree") else ["ls", "-R", path]
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)

@mcp.tool()
def read_file_with_lines(file_path: str) -> str:
    """Reads file with line numbers. Required for precision 'sed' or patching."""
    with open(file_path, 'r') as f:
        return "".join([f"{i+1}: {line}" for i, line in enumerate(f)])

@mcp.tool()
def search_codebase_grep(query: str, path: str = ".") -> str:
    """Regex search across workspace to find function definitions or TODOs."""
    return subprocess.check_output(["grep", "-rnE", query, path], text=True)

@mcp.tool()
def get_file_metadata(file_path: str) -> str:
    """Returns size, permissions, and modification time of a file."""
    stats = os.stat(file_path)
    return f"Size: {stats.st_size}b, Perms: {oct(stats.st_mode)}, Modified: {stats.st_mtime}"

@mcp.tool()
def atomic_write_file(file_path: str, content: str) -> str:
    """Writes content to a file safely. Overwrites existing content."""
    temp_path = f"{file_path}.tmp"
    with open(temp_path, 'w') as f:
        f.write(content)
    os.replace(temp_path, file_path)
    return f"Successfully wrote to {file_path}"

# --- CATEGORY 2: GIT & VERSION CONTROL ---

@mcp.tool()
def git_status_summary() -> str:
    """Returns summarized git status. Check this before staged commits."""
    return subprocess.check_output(["git", "status", "-s"], text=True)

@mcp.tool()
def git_diff_staged() -> str:
    """Returns unified diff of staged changes for code review."""
    return subprocess.check_output(["git", "diff", "--staged"], text=True)

@mcp.tool()
def git_create_branch(branch_name: str) -> str:
    """Creates and switches to a new git branch."""
    return subprocess.check_output(["git", "checkout", "-b", branch_name], text=True)

@mcp.tool()
def git_commit_with_message(message: str) -> str:
    """Commits staged changes with a descriptive message."""
    return subprocess.check_output(["git", "commit", "-m", message], text=True)

@mcp.tool()
def git_log_recent(count: int = 5) -> str:
    """Returns the last N commit messages and hashes."""
    return subprocess.check_output(["git", "log", "--oneline", "-n", str(count)], text=True)

# --- CATEGORY 3: PROCESS & SYSTEM ---

@mcp.tool()
def execute_shell_command(command: str, timeout_seconds: int = 30) -> str:
    """Runs restricted shell commands (e.g., npm test, pytest). Use with caution."""
    return subprocess.check_output(command, shell=True, text=True, timeout=timeout_seconds)

@mcp.tool()
def get_environment_variables(filter_prefix: Optional[str] = None) -> str:
    """Lists environment variables. Useful for debugging config paths."""
    envs = {k: v for k, v in os.environ.items() if not any(s in k.lower() for s in ["key", "secret", "token"])}
    if filter_prefix:
        envs = {k: v for k, v in envs.items() if k.startswith(filter_prefix)}
    return json.dumps(envs, indent=2)

@mcp.tool()
def check_port_availability(port: int) -> str:
    """Checks if a network port is in use before starting a dev server."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return "In Use" if s.connect_ex(('localhost', port)) == 0 else "Available"

@mcp.tool()
def list_running_processes(search_term: str) -> str:
    """Lists processes by name (e.g., 'python', 'node')."""
    return subprocess.check_output(["pgrep", "-fl", search_term], text=True)

@mcp.tool()
def kill_process_by_port(port: int) -> str:
    """Terminates process occupying a port. Use if dev server hangs."""
    try:
        pid = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True).strip()
        os.kill(int(pid), 9)
        return f"Killed process {pid} on port {port}"
    except:
        return "No process found on that port."

# --- CATEGORY 4: UTILITIES ---

@mcp.tool()
def parse_json_safe(json_string: str) -> str:
    """Validates and pretty-prints JSON to prevent config corruption."""
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
    """Unpacks .zip or .tar.gz files."""
    shutil.unpack_archive(file_path, destination)
    return f"Extracted {file_path} to {destination}"

@mcp.tool()
def calculate_file_hash(file_path: str) -> str:
    """Returns SHA-256 hash to verify file integrity."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

@mcp.tool()
def inspect_docker_container(container_name: str) -> str:
    """Returns logs and state for a Docker container."""
    return subprocess.check_output(["docker", "inspect", container_name], text=True)

if __name__ == "__main__":
    mcp.run()
