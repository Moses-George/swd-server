import asyncio, json, math, random
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..core.realtime import hub

router = APIRouter()


@router.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket):
    await ws.accept()
    q = await hub.subscribe()
    ticker_task = asyncio.create_task(_ticker())
    try:
        while True:
            msg = await q.get()
            await ws.send_text(msg)
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(q)
        ticker_task.cancel()


async def _ticker():
    """Publishes synthetic KPI updates every 2s so the UI has live data even
    without real sensors. Real deployments should stop this and ingest via
    POST /api/networks/{nid}/telemetry."""
    t = 0
    rng = random.Random()
    while True:
        await asyncio.sleep(2)
        t += 1
        await hub.publish("kpi", {
            "avg_pressure": round(44 + math.sin(t / 10) * 2 + rng.uniform(-0.5, 0.5), 2),
            "demand_now": round(138 + math.sin(t / 8) * 12, 1),
            "energy_kw": round(320 + math.sin(t / 6) * 60, 1),
        })
