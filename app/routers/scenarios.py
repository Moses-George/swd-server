from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_async_db
from ..models import Network, Node, Pipe, Scenario
from ..schemas import ScenarioRun, ScenarioOut
from ..core.security import current_user
from ..services.scenario import apply_scenario, network_metrics

router = APIRouter(prefix="/api/networks/{nid}/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(
    nid: int, db: AsyncSession = Depends(get_async_db), _=Depends(current_user)
):
    return (
        (
            await db.execute(
                select(Scenario)
                .where(Scenario.network_id == nid)
                .order_by(Scenario.id.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post("/run", response_model=ScenarioOut)
async def run(
    nid: int,
    body: ScenarioRun,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    net = await db.get(Network, nid)
    if not net:
        raise HTTPException(404)
    nodes = (
        (await db.execute(select(Node).where(Node.network_id == nid))).scalars().all()
    )
    pipes = (
        (await db.execute(select(Pipe).where(Pipe.network_id == nid))).scalars().all()
    )
    baseline = network_metrics(nodes, pipes)
    scen_nodes, scen_pipes = apply_scenario(nodes, pipes, body.kind, body.params)
    scen_metrics = network_metrics(scen_nodes, scen_pipes)
    s = Scenario(
        network_id=nid,
        name=body.name,
        kind=body.kind,
        params=body.params,
        baseline_metrics=baseline,
        scenario_metrics=scen_metrics,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/{sid}", status_code=204)
async def delete_scenario(
    nid: int,
    sid: int,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(current_user),
):
    s = await db.get(Scenario, sid)
    if s and s.network_id == nid:
        await db.delete(s)
        await db.commit()
