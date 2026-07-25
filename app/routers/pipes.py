# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from ..core.database import get_async_db
# from ..models import Pipe
# from ..schemas import PipeIn, PipeOut, PipePatch
# from ..core.security import current_user
# from ..core.realtime import hub

# router = APIRouter(prefix="/api/networks/{nid}/pipes", tags=["pipes"])


# @router.get("", response_model=list[PipeOut])
# async def list_pipes(
#     nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
# ):
#     return (
#         (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
#     )


# @router.post("", response_model=PipeOut)
# async def create_pipe(
#     nid: int,
#     body: PipeIn,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     p = Pipe(network_id=nid, **body.model_dump())
#     db.add(p)
#     await db.commit()
#     await db.refresh(p)
#     await hub.publish("pipe.created", {"network_id": nid, "id": p.id})
#     return p


# @router.patch("/{pipe_id}", response_model=PipeOut)
# async def patch_pipe(
#     nid: int,
#     pipe_id: int,
#     body: PipePatch,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     p = await db.get(Pipe, pipe_id)
#     if not p or p.network_id != nid:
#         raise HTTPException(404)
#     for k, v in body.model_dump(exclude_none=True).items():
#         setattr(p, k, v)
#     await db.commit()
#     await db.refresh(p)
#     await hub.publish("pipe.updated", {"network_id": nid, "id": p.id})
#     return p


# @router.delete("/{pipe_id}", status_code=204)
# async def delete_pipe(
#     nid: int,
#     pipe_id: int,
#     db: AsyncSession = Depends(get_async_db),
#     _=Depends(current_user),
# ):
#     p = await db.get(Pipe, pipe_id)
#     if p and p.network_id == nid:
#         await db.delete(p)
#         await db.commit()
#         await hub.publish("pipe.deleted", {"network_id": nid, "id": pipe_id})


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Pipe
from ..schemas import PipeIn, PipeOut, PipePatch
from ..core.security import current_user
from ..core.realtime import hub
from ..validators import validate_new_pipe, VALID_MATERIALS

router = APIRouter(prefix="/api/networks/{nid}/pipes", tags=["pipes"])


@router.get("", response_model=list[PipeOut])
async def list_pipes(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    return (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )


@router.post("", response_model=PipeOut)
async def create_pipe(
    nid: int,
    body: PipeIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    await validate_new_pipe(
        db, nid, body.ext_id, body.from_ext, body.to_ext, body.diameter, body.material
    )
    p = Pipe(network_id=nid, **body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    await hub.publish("pipe.created", {"network_id": nid, "id": p.id})
    return p


@router.patch("/{pipe_id}", response_model=PipeOut)
async def patch_pipe(
    nid: int,
    pipe_id: int,
    body: PipePatch,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    p = await db.get(Pipe, pipe_id)
    if not p or p.network_id != nid:
        raise HTTPException(404)
    patch = body.model_dump(exclude_none=True)
    if "diameter" in patch and patch["diameter"] <= 0:
        raise HTTPException(status_code=422, detail="diameter must be positive")
    if "material" in patch and patch["material"] not in VALID_MATERIALS:
        raise HTTPException(
            status_code=422, detail=f"Unknown material '{patch['material']}'"
        )
    if "age" in patch and patch["age"] < 0:
        raise HTTPException(status_code=422, detail="age cannot be negative")
    for k, v in patch.items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    await hub.publish("pipe.updated", {"network_id": nid, "id": p.id})
    return p


@router.delete("/{pipe_id}", status_code=204)
async def delete_pipe(
    nid: int,
    pipe_id: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    p = await db.get(Pipe, pipe_id)
    if p and p.network_id == nid:
        await db.delete(p)
        await db.commit()
        await hub.publish("pipe.deleted", {"network_id": nid, "id": pipe_id})
