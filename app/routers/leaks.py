from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random
from ..core.database import get_async_db
from ..models import Node, Pipe
from ..schemas import LeaksResponse, LeakOut
from ..core.security import current_user
from ..ml.inference import leak_probability
from ..core.realtime import hub

router = APIRouter(prefix="/api/networks/{nid}/leaks", tags=["leaks"])


@router.post("/detect", response_model=LeaksResponse)
async def detect(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    nodes = (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    by_node = {n.ext_id: n for n in nodes}
    inc: dict[str, list] = {n.ext_id: [] for n in nodes}
    for p in pipes:
        if p.from_ext in inc:
            inc[p.from_ext].append(p)
        if p.to_ext in inc:
            inc[p.to_ext].append(p)
    leaks: list[LeakOut] = []
    updated = 0
    rng = random.Random(42)
    for n in nodes:
        if n.type in ("reservoir", "tank"):
            continue
        residual = (n.pressure or 40) - 42 + rng.uniform(-2, 2)
        prob = leak_probability(n, inc[n.ext_id], residual)
        n.leak_prob = prob
        n.status = "alert" if prob > 0.7 else ("warn" if prob > 0.4 else "ok")
        updated += 1
        sev = (
            "critical"
            if prob > 0.7
            else "high" if prob > 0.4 else "medium" if prob > 0.2 else "low"
        )
        leaks.append(
            LeakOut(node_ext=n.ext_id, prob=round(prob, 3), zone=n.label, severity=sev)
        )
    await db.commit()
    leaks.sort(key=lambda x: -x.prob)
    await hub.publish("leaks.updated", {"network_id": nid, "count": updated})
    return LeaksResponse(leaks=leaks, updated_nodes=updated)
