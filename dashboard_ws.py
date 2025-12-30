# dashboard_ws.py
import asyncio
import json
from dashboard import clients

async def broadcast(event_name: str, payload: dict):
    data = json.dumps({"type": event_name, "payload": payload})
    dead = set()
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    for ws in dead:
        clients.remove(ws)

def connect_eventbus(event_bus):
    """
    Subscribe to all agentic system events and broadcast to dashboard.
    """
    for event_name in [
        "agent_start", "agent_done", "tool_call", "reward_assigned",
        "stage_enter", "stage_exit", "graph_event", "orchestrator_start", "orchestrator_done"
    ]:
        event_bus.on(event_name, lambda payload, en=event_name: broadcast(en, payload))
