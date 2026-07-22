from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Node
from ..schemas import ForecastOut, ForecastPoint
from ..core.security import current_user
from ..ml.inference import forecast_hourly

router = APIRouter(prefix="/api/networks/{nid}/forecast", tags=["forecast"])


@router.get("/hourly", response_model=ForecastOut)
async def hourly(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    consumers = (
        (
            await db.execute(
                select(Node).where(Node.network_id == nid, Node.type == "consumer")
            )
        )
        .scalars()
        .all()
    )
    total_ls = sum((c.demand or 0) for c in consumers)  # L/s
    base_ml_h = total_ls * 3.6 / 1000  # -> ML/h
    pts = forecast_hourly(base_ml_h or 6.0)
    return ForecastOut(horizon="24h", points=[ForecastPoint(**p) for p in pts])


@router.get("/weekly", response_model=ForecastOut)
async def weekly(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    consumers = (
        (
            await db.execute(
                select(Node).where(Node.network_id == nid, Node.type == "consumer")
            )
        )
        .scalars()
        .all()
    )
    total = sum((c.demand or 0) for c in consumers) * 86.4 or 145
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    pts = []
    for i, d in enumerate(days):
        fc = total + i * 3 + (6 if i % 2 else -2)
        pts.append(
            ForecastPoint(
                t=d,
                actual=fc - (4 if i % 2 else 2),
                forecast=fc,
                lower=fc - 8,
                upper=fc + 8,
            )
        )
    return ForecastOut(horizon="7d", points=pts)
