from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..core.database import get_async_db
from ..models import QualityReading
from ..schemas import QualityIn, QualityOut
from ..core.security import current_user

router = APIRouter(prefix="/api/networks/{nid}/quality", tags=["quality"])


@router.get("", response_model=list[QualityOut])
async def list_q(
    nid: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    return (
        (
            await db.execute(
                select(QualityReading)
                .where(QualityReading.network_id == nid)
                .order_by(desc(QualityReading.ts))
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


@router.post("", response_model=QualityOut)
async def add(
    nid: int,
    body: QualityIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    q = QualityReading(network_id=nid, **body.model_dump())
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q
