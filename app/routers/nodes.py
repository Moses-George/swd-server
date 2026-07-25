# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from ..core.database import get_async_db
# from ..models import Node
# from ..schemas import NodeIn, NodeOut, NodePatch
# from ..core.security import current_user
# from ..core.realtime import hub

# router = APIRouter(prefix="/api/networks/{nid}/nodes", tags=["nodes"])


# @router.get("", response_model=list[NodeOut])
# async def list_nodes(
#     nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
# ):
#     return (
#         (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
#     )


# @router.post("", response_model=NodeOut)
# async def create_node(
#     nid: int,
#     body: NodeIn,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     n = Node(network_id=nid, **body.model_dump())
#     db.add(n)
#     await db.commit()
#     await db.refresh(n)
#     await hub.publish(
#         "node.created", {"network_id": nid, "id": n.id, "ext_id": n.ext_id}
#     )
#     return n


# @router.patch("/{node_id}", response_model=NodeOut)
# async def patch_node(
#     nid: int,
#     node_id: int,
#     body: NodePatch,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     n = await db.get(Node, node_id)
#     if not n or n.network_id != nid:
#         raise HTTPException(404)
#     for k, v in body.model_dump(exclude_none=True).items():
#         setattr(n, k, v)
#     await db.commit()
#     await db.refresh(n)
#     await hub.publish("node.updated", {"network_id": nid, "id": n.id})
#     return n


# @router.delete("/{node_id}", status_code=204)
# async def delete_node(
#     nid: int,
#     node_id: int,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     n = await db.get(Node, node_id)
#     if n and n.network_id == nid:
#         await db.delete(n)
#         await db.commit()
#         await hub.publish("node.deleted", {"network_id": nid, "id": node_id})


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Node
from ..schemas import NodeIn, NodeOut, NodePatch
from ..core.security import current_user
from ..core.realtime import hub
from ..validators import (
    validate_new_node,
    validate_coords,
    validate_node_business_rules,
)

router = APIRouter(prefix="/api/networks/{nid}/nodes", tags=["nodes"])


@router.get("", response_model=list[NodeOut])
async def list_nodes(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    return (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )


@router.post("", response_model=NodeOut)
async def create_node(
    nid: int,
    body: NodeIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    await validate_new_node(
        db,
        nid,
        body.ext_id,
        body.type,
        body.x,
        body.y,
        rated_kw=body.rated_kw,
        demand=body.demand,
        level=body.level,
        elevation=body.elevation,
    )
    n = Node(network_id=nid, **body.model_dump())
    db.add(n)
    await db.commit()
    await db.refresh(n)
    await hub.publish(
        "node.created", {"network_id": nid, "id": n.id, "ext_id": n.ext_id}
    )
    return n


@router.patch("/{node_id}", response_model=NodeOut)
async def patch_node(
    nid: int,
    node_id: int,
    body: NodePatch,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    n = await db.get(Node, node_id)
    if not n or n.network_id != nid:
        raise HTTPException(404)
    patch = body.model_dump(exclude_none=True)
    # Merge & validate move + property constraints against final state
    new_x = patch.get("x", n.x)
    new_y = patch.get("y", n.y)
    validate_coords(new_x, new_y)
    validate_node_business_rules(
        n.type,
        patch.get("rated_kw", n.rated_kw),
        patch.get("demand", n.demand),
        patch.get("level", n.level),
        patch.get("elevation", n.elevation),
    )
    for k, v in patch.items():
        setattr(n, k, v)
    await db.commit()
    await db.refresh(n)
    await hub.publish("node.updated", {"network_id": nid, "id": n.id})
    return n


@router.delete("/{node_id}", status_code=204)
async def delete_node(
    nid: int,
    node_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    n = await db.get(Node, node_id)
    if n and n.network_id == nid:
        await db.delete(n)
        await db.commit()
        await hub.publish("node.deleted", {"network_id": nid, "id": node_id})
