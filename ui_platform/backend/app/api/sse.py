"""
sse.py

Server-Sent Events (SSE) endpoint for real-time observability.

Streams:
- Stage start
- Stage completion
- Errors
- Final output

Designed for React Flow live graph lighting.
"""

from fastapi import APIRouter
from fastapi.responses import EventSourceResponse
import asyncio
from app.api.runs import _RUNS

router = APIRouter(tags=["events"])


@router.get("/runs/{run_id}")
async def stream_run(run_id: str):
    """
    Stream execution events for a run.

    Events are emitted as:
    - stage_started
    - stage_completed
    - run_completed
    """

    async def event_generator():
        if run_id not in _RUNS:
            yield {"event": "error", "data": "Run not found"}
            return

        run = _RUNS[run_id]

        # Simulated execution for demo
        for stage in ["ideation", "planning", "execution"]:
            event = {
                "stage": stage,
                "status": "running",
            }
            yield {"event": "stage_update", "data": event}
            await asyncio.sleep(1)

            event["status"] = "completed"
            yield {"event": "stage_update", "data": event}
            await asyncio.sleep(0.5)

        yield {"event": "run_completed", "data": {"status": "success"}}

    return EventSourceResponse(event_generator())
