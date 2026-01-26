import asyncio
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
import json
from pathlib import Path

console = Console()

def save_checkpoint(mission_id: str, state: dict):
    Path("checkpoints").mkdir(exist_ok=True)
    with open(f"checkpoints/{mission_id}.json", "w") as f:
        json.dump(state, f, indent=4)

def load_checkpoint(mission_id: str):
    path = Path(f"checkpoints/{mission_id}.json")
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None

async def run_cli_session(engine, initial_state):
    state = initial_state
    
    # The "Pulse" Loop
    while True:
        # 1. Display Current Control Plane (The Artifact)
        console.print(Panel(Markdown(state["control_raw"]), title="[bold blue]Current Mission Plan"))

        # 2. Run the Engine until it hits a Breakpoint or Ends
        async for event in engine.run_mission(state):
            # Stream tool logs to the console
            if "agent" in event:
                for t_json in event["agent"].get("tool_raw", []):
                    t = ToolEnvelope.model_validate_json(t_json)
                    color = "green" if t.success else "red"
                    console.print(f"[{color}]> Tool: {t.tool_name} | Status: {'Success' if t.success else 'Error'}")
            
            # Capture the updated state from the event
            state.update(list(event.values())[0])

        # 3. Check for HITL (Breakpoint)
        if "[ ]" in state["control_raw"]:
            # If the last tool was a request for human input
            last_tool = ToolEnvelope.model_validate_json(state["tool_raw"][-1])
            if "human" in last_tool.tool_name:
                console.print(f"\n[bold yellow]HITL REQUIRED: {last_tool.output.get('reason')}")
                user_input = console.input("[bold cyan]Your Response > ")
                
                # Create the response envelope to "resume"
                # (Logic from previous step to inject user_input)
                state["tool_raw"].append(create_human_envelope(user_input))
                continue # Loop back to let the Architect process your answer
        else:
            console.print("[bold green]Mission Accomplished.")
            break


def show_help():
    """Custom help display for the Agnostic OS CLI"""
    table = Table(title="Agnostic OS - CLI Surface Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    table.add_row("--mission", "The unique ID for the task (used for saving/loading)")
    table.add_row("--domain", "The domain repo to use (e.g., realestate, devops)")
    table.add_row("--template", "Path to the .md file to initialize the Control Plane")
    table.add_row("--reset", "Clear existing checkpoint and start fresh")
    console.print(table)

async def main():
    parser = argparse.ArgumentParser(description="Agnostic OS CLI Surface")
    parser.add_argument("--mission", type=str, required=True, help="Unique mission ID")
    parser.add_argument("--domain", type=str, help="Domain ID (e.g. realestate)")
    parser.add_argument("--template", type=str, help="Path to initial .md template")
    parser.add_argument("--reset", action="store_true", help="Reset mission state")

    args = parser.parse_args()

    # 1. Load or Initialize State
    state = None if args.reset else load_checkpoint(args.mission)
    
    if not state:
        if not args.domain or not args.template:
            console.print("[bold red]Error:[/] New missions require --domain and --template.")
            show_help()
            return
            
        with open(args.template, "r") as f:
            template_content = f.read()
            
        state = {
            "domain": args.domain,
            "stage": "initialization",
            "control_raw": template_content,
            "data_raw": json.dumps({"address": "123 Maple St"}), # Default starting data
            "tool_raw": []
        }

    # 2. Run the Session
    console.print(f"[bold green]Starting Mission:[/] {args.mission}")
    await run_cli_session(state, args.mission)

async def run_cli_session(state, mission_id):
    # (Previous engine loop logic here...)
    # Inside the loop, after every node completes:
    save_checkpoint(mission_id, state)

if __name__ == "__main__":
    asyncio.run(main())
