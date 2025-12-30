# tools/runtime.py
import asyncio

class ToolExecutionError(Exception):
    pass


async def execute_with_retry(
    tool_fn,
    payload,
    *,
    retries: int = 3,
    backoff: float = 0.5,
):
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            return await tool_fn(payload)
        except Exception as e:
            last_exc = e
            await asyncio.sleep(backoff * attempt)

    raise ToolExecutionError(str(last_exc))

