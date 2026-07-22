from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Node
from ..schemas import CarbonOut
from ..core.security import current_user

router = APIRouter(prefix="/api/networks/{nid}/carbon", tags=["carbon"])
GRID_FACTOR = 0.38  # kg CO2 / kWh


@router.get("", response_model=CarbonOut)
async def carbon(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    pumps = (
        (
            await db.execute(
                select(Node).where(Node.network_id == nid, Node.type == "pump")
            )
        )
        .scalars()
        .all()
    )
    kwh = sum((p.rated_kw or 0) * 0.65 * 24 for p in pumps)
    trend = [round(kwh * (0.92 + 0.03 * i), 1) for i in range(7)]
    return CarbonOut(
        kwh_today=round(kwh, 1),
        kg_co2_today=round(kwh * GRID_FACTOR, 1),
        grid_factor=GRID_FACTOR,
        trend_7d=trend,
    )
