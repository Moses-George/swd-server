from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..core.database import get_async_db
from ..models import Telemetry
from ..schemas import TelemetryIn, TelemetryOut
from ..core.security import current_user
from ..core.realtime import hub

router = APIRouter(prefix="/api/networks/{nid}/telemetry", tags=["telemetry"])


@router.post("", response_model=TelemetryOut)
async def ingest(
    nid: int,
    body: TelemetryIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    t = Telemetry(network_id=nid, **body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await hub.publish(
        "telemetry",
        {
            "network_id": nid,
            "node_ext": t.node_ext,
            "metric": t.metric,
            "value": t.value,
            "ts": t.ts.isoformat(),
        },
    )
    return t


@router.get("", response_model=list[TelemetryOut])
async def recent(
    nid: int,
    limit: int = 200,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    q = (
        select(Telemetry)
        .where(Telemetry.network_id == nid)
        .order_by(desc(Telemetry.ts))
        .limit(limit)
    )
    return (await db.execute(q)).scalars().all()
