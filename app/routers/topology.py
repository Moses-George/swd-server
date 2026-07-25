"""Topology bulk-replace + full integrity validation.

- POST /replace       : atomic snapshot restore (used by undo/redo)
- GET  /validate      : full integrity report of the persisted topology
- POST /validate      : dry-run integrity report against a candidate snapshot
"""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_db
from ..models import Network, Node, Pipe
from ..schemas import NodeIn, NodeOut, PipeIn, PipeOut
from ..core.security import current_user
from ..core.realtime import hub
from ..validators import (
    COORD_MAX,
    COORD_MIN,
    VALID_MATERIALS,
    VALID_NODE_TYPES,
)

router = APIRouter(prefix="/api/networks/{nid}/topology", tags=["topology"])


class TopologyIn(BaseModel):
    nodes: list[NodeIn]
    pipes: list[PipeIn]


class TopologyOut(BaseModel):
    nodes: list[NodeOut]
    pipes: list[PipeOut]


class IssueLocation(BaseModel):
    kind: Literal["node", "pipe", "graph"]
    ext_id: str | None = None
    ext_ids: list[str] | None = None
    x: float | None = None
    y: float | None = None


class Issue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    location: IssueLocation
    hint: str | None = None


class ValidationReport(BaseModel):
    network_id: int
    ok: bool
    node_count: int
    pipe_count: int
    issues: list[Issue]


# ---------- shared integrity checker ---------------------------------------


def _integrity_report(nid: int, nodes: list, pipes: list) -> ValidationReport:
    """Runs a full topology integrity pass and returns a structured report.

    `nodes` / `pipes` accept ORM rows OR Pydantic NodeIn/PipeIn — attribute
    access is uniform because both expose ext_id/type/x/... .
    """
    issues: list[Issue] = []

    seen_node: dict[str, object] = {}
    node_types: dict[str, str] = {}

    for n in nodes:
        ext = getattr(n, "ext_id", "")
        if not ext or not str(ext).strip():
            issues.append(
                Issue(
                    severity="error",
                    code="NODE_MISSING_EXT_ID",
                    message="Node is missing ext_id",
                    location=IssueLocation(kind="node"),
                    hint="Assign a unique identifier to every node.",
                )
            )
            continue
        if ext in seen_node:
            issues.append(
                Issue(
                    severity="error",
                    code="NODE_DUPLICATE_EXT_ID",
                    message=f"Duplicate node ext_id '{ext}'",
                    location=IssueLocation(kind="node", ext_id=ext),
                    hint="Node ext_ids must be unique within a network.",
                )
            )
            continue
        seen_node[ext] = n
        node_types[ext] = getattr(n, "type", "")

        x, y = getattr(n, "x", None), getattr(n, "y", None)
        if (
            x is None
            or y is None
            or not (COORD_MIN <= x <= COORD_MAX)
            or not (COORD_MIN <= y <= COORD_MAX)
        ):
            issues.append(
                Issue(
                    severity="error",
                    code="NODE_COORD_OUT_OF_BOUNDS",
                    message=f"Node '{ext}' has out-of-bounds coordinates",
                    location=IssueLocation(kind="node", ext_id=ext, x=x, y=y),
                    hint=f"x and y must be within [{COORD_MIN}, {COORD_MAX}].",
                )
            )

        ntype = getattr(n, "type", "")
        if ntype not in VALID_NODE_TYPES:
            issues.append(
                Issue(
                    severity="error",
                    code="NODE_INVALID_TYPE",
                    message=f"Node '{ext}' has unknown type '{ntype}'",
                    location=IssueLocation(kind="node", ext_id=ext),
                )
            )

        rated_kw = getattr(n, "rated_kw", None)
        if ntype == "pump" and (rated_kw is None or rated_kw <= 0):
            issues.append(
                Issue(
                    severity="error",
                    code="PUMP_MISSING_RATED_KW",
                    message=f"Pump '{ext}' requires a positive rated_kw",
                    location=IssueLocation(kind="node", ext_id=ext),
                    hint="Set the pump's rated power in kW.",
                )
            )

        level = getattr(n, "level", None)
        if ntype == "tank" and level is not None and not (0 <= level <= 100):
            issues.append(
                Issue(
                    severity="warning",
                    code="TANK_LEVEL_OUT_OF_RANGE",
                    message=f"Tank '{ext}' level {level}% is outside 0..100",
                    location=IssueLocation(kind="node", ext_id=ext),
                )
            )

    # Pipe checks --------------------------------------------------------
    seen_pipe: set[str] = set()
    seen_pair: set[frozenset[str]] = set()
    degree: dict[str, int] = {ext: 0 for ext in node_types}
    adjacency: dict[str, set[str]] = {ext: set() for ext in node_types}

    for p in pipes:
        pid = getattr(p, "ext_id", "")
        if not pid or not str(pid).strip():
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_MISSING_EXT_ID",
                    message="Pipe is missing ext_id",
                    location=IssueLocation(kind="pipe"),
                )
            )
            continue
        if pid in seen_pipe:
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_DUPLICATE_EXT_ID",
                    message=f"Duplicate pipe ext_id '{pid}'",
                    location=IssueLocation(kind="pipe", ext_id=pid),
                )
            )
            continue
        seen_pipe.add(pid)

        f, t = getattr(p, "from_ext", ""), getattr(p, "to_ext", "")
        if f == t:
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_SELF_LOOP",
                    message=f"Pipe '{pid}' connects '{f}' to itself",
                    location=IssueLocation(kind="pipe", ext_id=pid, ext_ids=[f]),
                )
            )
        missing = [e for e in (f, t) if e and e not in node_types]
        for m in missing:
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_ENDPOINT_MISSING",
                    message=f"Pipe '{pid}' references non-existent node '{m}'",
                    location=IssueLocation(kind="pipe", ext_id=pid, ext_ids=[m]),
                    hint="Add the endpoint node or remove the pipe.",
                )
            )
        if not missing and f != t:
            pair = frozenset({f, t})
            if pair in seen_pair:
                issues.append(
                    Issue(
                        severity="error",
                        code="PIPE_DUPLICATE_PAIR",
                        message=f"Duplicate pipe between '{f}' and '{t}'",
                        location=IssueLocation(kind="pipe", ext_id=pid, ext_ids=[f, t]),
                    )
                )
            else:
                seen_pair.add(pair)
                degree[f] = degree.get(f, 0) + 1
                degree[t] = degree.get(t, 0) + 1
                adjacency.setdefault(f, set()).add(t)
                adjacency.setdefault(t, set()).add(f)
            if {node_types.get(f), node_types.get(t)} == {"reservoir"}:
                issues.append(
                    Issue(
                        severity="error",
                        code="RESERVOIR_TO_RESERVOIR",
                        message=f"Pipe '{pid}' connects two reservoirs directly",
                        location=IssueLocation(kind="pipe", ext_id=pid, ext_ids=[f, t]),
                        hint="Route reservoirs through a pump, valve, or junction.",
                    )
                )

        dia = getattr(p, "diameter", 0)
        if dia is None or dia <= 0:
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_DIAMETER_INVALID",
                    message=f"Pipe '{pid}' has non-positive diameter",
                    location=IssueLocation(kind="pipe", ext_id=pid),
                )
            )
        mat = getattr(p, "material", "")
        if mat not in VALID_MATERIALS:
            issues.append(
                Issue(
                    severity="error",
                    code="PIPE_MATERIAL_INVALID",
                    message=f"Pipe '{pid}' has unknown material '{mat}'",
                    location=IssueLocation(kind="pipe", ext_id=pid),
                )
            )

    # Graph-level checks --------------------------------------------------
    for ext, ntype in node_types.items():
        d = degree.get(ext, 0)
        if d == 0 and ntype != "reservoir":
            issues.append(
                Issue(
                    severity="warning",
                    code="NODE_ORPHAN",
                    message=f"Node '{ext}' has no connected pipes",
                    location=IssueLocation(kind="node", ext_id=ext),
                    hint="Connect it with a pipe or delete it.",
                )
            )

    # Reservoir reachability: every non-reservoir must reach a reservoir/tank.
    sources = {ext for ext, t in node_types.items() if t in ("reservoir", "tank")}
    if sources:
        reachable: set[str] = set()
        stack = list(sources)
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            stack.extend(adjacency.get(cur, ()))
        unreached = [
            ext
            for ext, t in node_types.items()
            if t not in ("reservoir",) and ext not in reachable
        ]
        for ext in unreached:
            issues.append(
                Issue(
                    severity="warning",
                    code="NODE_UNREACHABLE_FROM_SOURCE",
                    message=f"Node '{ext}' cannot reach any reservoir or tank",
                    location=IssueLocation(kind="node", ext_id=ext),
                    hint="Add a pipe path back to a supply source.",
                )
            )
    else:
        issues.append(
            Issue(
                severity="warning",
                code="NO_SUPPLY_SOURCE",
                message="Network has no reservoir or tank as supply source",
                location=IssueLocation(kind="graph"),
            )
        )

    ok = not any(i.severity == "error" for i in issues)
    return ValidationReport(
        network_id=nid,
        ok=ok,
        node_count=len(node_types),
        pipe_count=len(seen_pipe),
        issues=issues,
    )


# ---------- routes ---------------------------------------------------------


@router.post("/replace", response_model=TopologyOut)
async def replace_topology(
    nid: int,
    body: TopologyIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    if not await db.get(Network, nid):
        raise HTTPException(404, "Network not found")

    report = _integrity_report(nid, body.nodes, body.pipes)
    if not report.ok:
        # Return the structured report so the UI can highlight where it broke.
        raise HTTPException(status_code=422, detail=report.model_dump())

    await db.execute(delete(Pipe).where(Pipe.network_id == nid))
    await db.execute(delete(Node).where(Node.network_id == nid))
    await db.flush()

    for n in body.nodes:
        db.add(Node(network_id=nid, **n.model_dump()))
    await db.flush()
    for p in body.pipes:
        db.add(Pipe(network_id=nid, **p.model_dump()))
    await db.commit()

    nodes = (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    await hub.publish(
        "topology.replaced",
        {"network_id": nid, "nodes": len(nodes), "pipes": len(pipes)},
    )
    return {"nodes": nodes, "pipes": pipes}


@router.get("/validate", response_model=ValidationReport)
async def validate_persisted(
    nid: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    """Runs a full integrity check against what is currently in the database."""
    if not await db.get(Network, nid):
        raise HTTPException(404, "Network not found")
    nodes = (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    return _integrity_report(nid, list(nodes), list(pipes))


@router.post("/validate", response_model=ValidationReport)
async def validate_snapshot(
    nid: int,
    body: TopologyIn,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    """Dry-run integrity check for a client-supplied candidate topology."""
    if not await db.get(Network, nid):
        raise HTTPException(404, "Network not found")
    return _integrity_report(nid, body.nodes, body.pipes)
