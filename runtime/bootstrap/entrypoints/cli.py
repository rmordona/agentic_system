import argparse
import asyncio
from pathlib import Path
#import logging

from runtime.bootstrap.platform import Platform
from runtime.runtime_manager import RuntimeManager
from runtime.workspace_hub import WorkspaceHub
from runtime.logger import AgentLogger

# --------------------------------------------------
# Logging
# --------------------------------------------------
aloha = None

# -----------------------------
# CLI Argument Parsing
# -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Run a task through the agentic platform CLI")
    parser.add_argument("--workspace", type=str, required=True, help="Workspace name or path")
    parser.add_argument("--message", type=str, required=True, help="User task message")
    parser.add_argument("--user_id", type=str, required=True, help="User ID for session tracking")
    parser.add_argument("--session_id", type=str, help="Optional existing session ID")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

async def main():
    args = parse_args()

    workspaces_root = Path("workspaces")

    # 1. Initialize Platform (singleton shared resources)
    Platform.initialize( workspaces_root= workspaces_root )

    # 2. Discover workspace via WorkspaceHub
    #workspace_hub = WorkspaceHub(workspaces_root=workspaces_root)
    #workspace_path = workspace_hub.resolve(args.workspace)
    #if not workspace_path.exists():
    #    logger.error(f"Workspace '{args.workspace}' not found")
    #    return

    workspace_hub = Platform.workspace_hub


    # 3. Create or get workspace RuntimeManager (singleton per workspace)
    runtime = workspace_hub.get_runtime(args.workspace)

    # runtime = workspace_hub.get_runtime(args.workspace)

    result = await runtime.run_user_message(
        user_message=args.message,
        session_id=args.session_id, # optional
        verbose=args.verbose
    )

    # 4. Run user task through orchestrator

    print("==== Task Result ====")
    print(f"Workspace: {workspaces_root.name}")
    print(f"User ID: {args.user_id}")
    print(f"Session ID: {args.session_id}")
    print(f"Task: {args.message}")
    print("Result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
