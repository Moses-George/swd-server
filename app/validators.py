"""Server-side validators for network topology mutations."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Node, Pipe

# Coordinate bounds (SVG viewport is 0..100 both axes, we accept a small margin).
COORD_MIN = 0.0
COORD_MAX = 100.0

VALID_NODE_TYPES = {"reservoir", "tank", "pump", "valve", "junction", "consumer"}
VALID_MATERIALS = {"PVC", "DI", "Steel", "HDPE"}


def validate_coords(x: float | None, y: float | None) -> None:
    if x is not None and not (COORD_MIN <= x <= COORD_MAX):
        raise HTTPException(
            status_code=422, detail=f"x must be within [{COORD_MIN}, {COORD_MAX}]"
        )
    if y is not None and not (COORD_MIN <= y <= COORD_MAX):
        raise HTTPException(
            status_code=422, detail=f"y must be within [{COORD_MIN}, {COORD_MAX}]"
        )


def validate_node_business_rules(
    ntype: str,
    rated_kw: float | None,
    demand: float | None,
    level: float | None,
    elevation: float | None,
) -> None:
    if ntype not in VALID_NODE_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown node type '{ntype}'")
    if ntype == "pump":
        if rated_kw is None or rated_kw <= 0:
            raise HTTPException(
                status_code=422, detail="Pump requires positive rated_kw"
            )
    if ntype == "tank" and level is not None and not (0 <= level <= 100):
        raise HTTPException(
            status_code=422, detail="Tank level must be 0..100 (percent)"
        )
    if ntype == "consumer" and demand is not None and demand < 0:
        raise HTTPException(
            status_code=422, detail="Consumer demand cannot be negative"
        )
    if elevation is not None and (elevation < -500 or elevation > 5000):
        raise HTTPException(
            status_code=422, detail="Elevation out of realistic range (-500..5000 m)"
        )


async def validate_new_node(
    db: AsyncSession,
    nid: int,
    ext_id: str,
    ntype: str,
    x: float,
    y: float,
    rated_kw: float | None = None,
    demand: float | None = None,
    level: float | None = None,
    elevation: float | None = None,
) -> None:
    if not ext_id or not ext_id.strip():
        raise HTTPException(status_code=422, detail="ext_id is required")
    validate_coords(x, y)
    validate_node_business_rules(ntype, rated_kw, demand, level, elevation)
    dup = (
        await db.execute(
            select(Node.id).where(Node.network_id == nid, Node.ext_id == ext_id)
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(
            status_code=409, detail=f"Node with ext_id '{ext_id}' already exists"
        )


async def validate_new_pipe(
    db: AsyncSession,
    nid: int,
    ext_id: str,
    from_ext: str,
    to_ext: str,
    diameter: float,
    material: str,
) -> None:
    if not ext_id or not ext_id.strip():
        raise HTTPException(status_code=422, detail="ext_id is required")
    if from_ext == to_ext:
        raise HTTPException(status_code=422, detail="Pipe endpoints must differ")
    if diameter is None or diameter <= 0:
        raise HTTPException(status_code=422, detail="Pipe diameter must be positive")
    if material not in VALID_MATERIALS:
        raise HTTPException(status_code=422, detail=f"Unknown material '{material}'")

    endpoints = (
        await db.execute(
            select(Node.ext_id, Node.type).where(
                Node.network_id == nid, Node.ext_id.in_([from_ext, to_ext])
            )
        )
    ).all()
    found = {row[0]: row[1] for row in endpoints}
    for e in (from_ext, to_ext):
        if e not in found:
            raise HTTPException(
                status_code=422,
                detail=f"Endpoint node '{e}' does not exist in this network",
            )
    if {found[from_ext], found[to_ext]} == {"reservoir"}:
        raise HTTPException(
            status_code=422, detail="Cannot connect two reservoirs directly"
        )

    dup_ext = (
        await db.execute(
            select(Pipe.id).where(Pipe.network_id == nid, Pipe.ext_id == ext_id)
        )
    ).scalar_one_or_none()
    if dup_ext is not None:
        raise HTTPException(
            status_code=409, detail=f"Pipe with ext_id '{ext_id}' already exists"
        )

    dup_pair = (
        await db.execute(
            select(Pipe.id).where(
                Pipe.network_id == nid,
                ((Pipe.from_ext == from_ext) & (Pipe.to_ext == to_ext))
                | ((Pipe.from_ext == to_ext) & (Pipe.to_ext == from_ext)),
            )
        )
    ).scalar_one_or_none()
    if dup_pair is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Pipe between '{from_ext}' and '{to_ext}' already exists",
        )
