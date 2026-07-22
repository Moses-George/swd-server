from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Node, Pipe, WorkOrder
from ..schemas import AssetHealth, WorkOrderIn, WorkOrderOut
from ..core.security import current_user

router = APIRouter(prefix="/api/networks/{nid}/maintenance", tags=["maintenance"])


@router.get("/health", response_model=list[AssetHealth])
async def health(
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
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    out: list[AssetHealth] = []
    for p in pumps:
        wear = min(int((p.rated_kw or 100) * 0.3), 90)
        health_ = max(20, 100 - wear)
        rul = max(10, 400 - wear * 4)
        out.append(
            AssetHealth(
                id=p.ext_id,
                type="Pump",
                rul=rul,
                health=health_,
                cycles=int(wear) * 1200,
                note="Nominal" if health_ > 60 else "Bearing wear detected",
            )
        )
    for pipe in pipes:
        wear = min(pipe.age * 2 + (20 if pipe.material == "Steel" else 5), 90)
        out.append(
            AssetHealth(
                id=pipe.ext_id,
                type=f"Pipe ({pipe.material}, {pipe.age}y)",
                rul=max(30, 400 - wear * 3),
                health=max(20, 100 - wear),
                cycles=0,
                note="Corrosion risk" if wear > 60 else "Nominal",
            )
        )
    return sorted(out, key=lambda a: a.health)


@router.get("/orders", response_model=list[WorkOrderOut])
async def list_orders(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    return (
        (
            await db.execute(
                select(WorkOrder)
                .where(WorkOrder.network_id == nid)
                .order_by(WorkOrder.id.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post("/orders", response_model=WorkOrderOut)
async def create_order(
    nid: int,
    body: WorkOrderIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    w = WorkOrder(network_id=nid, **body.model_dump())
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


@router.patch("/orders/{wid}/close", response_model=WorkOrderOut)
async def close_order(
    nid: int,
    wid: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    w = await db.get(WorkOrder, wid)
    if w:
        w.status = "closed"
        await db.commit()
        await db.refresh(w)
    return w
