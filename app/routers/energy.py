from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Node
from ..schemas import ScheduleOut
from ..core.security import current_user
from ..ml.inference import optimize_pump_schedule

router = APIRouter(prefix="/api/networks/{nid}/energy", tags=["energy"])


@router.post("/optimize", response_model=ScheduleOut)
async def optimize(
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
    if not pumps:
        raise HTTPException(400, "no pumps in network")
    result = optimize_pump_schedule([{"rated_kw": p.rated_kw or 0} for p in pumps])
    return result
