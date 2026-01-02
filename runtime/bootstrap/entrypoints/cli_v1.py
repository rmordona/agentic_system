# cli.py
import argparse
import asyncio
from runtime.singleton_resources import SingletonResources
from runtime.runtime_factory import get_runtime

session_control = SingletonResources.session_control  # singleton instance

def parse_args():
    parser = argparse.ArgumentParser(description="Run a task through the agentic system CLI")
    parser.add_argument("--task", type=str, required=True, help="Task description to run")
    parser.add_argument("--user_id", type=str, required=True, help="User ID for session tracking")
    parser.add_argument("--session_id", type=str, required=False, help="Optional existing session ID")
    return parser.parse_args()

async def main():
    args = parse_args()

    # Resolve or create session automatically via Runtime
    runtime = get_runtime(session_id=args.session_id, user_id=args.user_id)

    # Run the task
    result = await runtime.run(args.task)

    print("==== Task Result ====")
    print(f"User ID: {args.user_id}")
    print(f"Session ID: {session_control.session_id if hasattr(runtime, 'session_control') else args.session_id}")
    print(f"Task: {args.task}")
    print("Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
