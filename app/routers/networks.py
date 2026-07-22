from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Network, Node, Pipe
from ..schemas import NetworkIn, NetworkOut
from ..core.security import current_user

router = APIRouter(prefix="/api/networks", tags=["networks"])


@router.get("", response_model=list[NetworkOut])
async def list_networks(
    db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    return (await db.execute(select(Network).order_by(Network.id))).scalars().all()


@router.post("", response_model=NetworkOut)
async def create(
    body: NetworkIn, db: AsyncSession = Depends(get_async_db), u=Depends(current_user)
):
    n = Network(name=body.name, owner_id=u.id)
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


@router.get("/{nid}/export")
async def export_epanet(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    n = await db.get(Network, nid)
    if not n:
        raise HTTPException(404)
    nodes = (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    return {
        "network": n.name,
        "nodes": [
            {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in nodes
        ],
        "pipes": [
            {c.name: getattr(x, c.name) for c in x.__table__.columns} for x in pipes
        ],
    }


@router.delete("/{nid}", status_code=204)
async def delete(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    n = await db.get(Network, nid)
    if n:
        await db.delete(n)
        await db.commit()
