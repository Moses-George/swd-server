"""In-process pub/sub for WebSocket fan-out. Optional Redis passthrough."""
import asyncio, json
from typing import Any


class Hub:
    def __init__(self):
        self._subs: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    async def publish(self, event: str, data: Any) -> None:
        msg = json.dumps({"event": event, "data": data}, default=str)
        for q in list(self._subs):
            if q.full():
                try: q.get_nowait()
                except Exception: pass
            await q.put(msg)


hub = Hub()