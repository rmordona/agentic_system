# events/event_bus.py
import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Any


class EventBus:
    """
    Async event bus supporting decorator-style and direct subscriptions.
    """

    def __init__(self):
        self._subscribers = defaultdict(list)

    def on(self, event_name: str):
        """
        Decorator-based event subscription.

        Usage:
            @event_bus.on("agent_start")
            async def handler(event): ...
        """

        def decorator(callback: Callable[[Any], Awaitable[None] | None]):
            self._subscribers[event_name].append(callback)
            return callback

        return decorator

    async def emit(self, event_name: str, payload: Any):
        """
        Emit an event to all subscribers.
        """
        if event_name not in self._subscribers:
            return

        coros = []
        for cb in self._subscribers[event_name]:
            result = cb(payload)
            if asyncio.iscoroutine(result):
                coros.append(result)

        if coros:
            await asyncio.gather(*coros)


    def emit_sync(self, event: str, payload: dict):
        """
        Safe sync wrapper for lifecycle hooks.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.emit(event, payload))
        else:
            asyncio.run(self.emit(event, payload))

    def subscribe(self, event: str, callback):
        self._subscribers.setdefault(event, []).append(callback)
