from datetime import datetime, timezone
import sys
from pathlib import Path

# Add the parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

"""Seed the DB with the default demo network + a demo user."""

import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models import User, Network, Node, Pipe
from core.security import hash_password

NODES = [
    (
        "R1",
        "reservoir",
        "Northfield Reservoir",
        8,
        18,
        62,
        None,
        None,
        None,
        30,
        None,
        "ok",
    ),
    ("T1", "tank", "Elevated Tank A", 32, 12, 55, None, 78, None, 25, None, "ok"),
    ("T2", "tank", "Ground Tank B", 72, 22, 42, None, 41, None, 10, None, "warn"),
    ("P1", "pump", "Pump Station 1", 20, 30, 58, None, None, 420, 15, None, "ok"),
    ("P2", "pump", "Pump Station 2", 55, 45, 51, None, None, 280, 12, None, "ok"),
    ("P3", "pump", "Pump Station 3", 82, 55, 34, None, None, 180, 8, None, "alert"),
    ("V1", "valve", "PRV-1", 40, 55, 46, None, None, None, 10, None, "ok"),
    ("V2", "valve", "PRV-2", 65, 70, 38, None, None, None, 8, None, "ok"),
    ("J1", "junction", "J-12", 30, 55, 44, None, None, None, 10, 0.97, "ok"),
    ("J2", "junction", "J-5", 48, 30, 50, None, None, None, 12, 0.04, "ok"),
    ("J3", "junction", "J-30", 75, 40, 39, None, None, None, 9, 0.01, "ok"),
    ("J4", "junction", "J-18", 22, 72, 41, None, None, None, 7, 0.62, "warn"),
    ("C1", "consumer", "District 1", 15, 85, 33, 24, None, None, 5, None, "ok"),
    ("C2", "consumer", "District 2", 42, 82, 30, 31, None, None, 4, None, "ok"),
    ("C3", "consumer", "District 3", 68, 88, 26, 19, None, None, 3, None, "warn"),
    ("C4", "consumer", "District 4", 88, 80, 22, 15, None, None, 3, None, "alert"),
]

PIPES = [
    ("PP1", "R1", "P1", 400, 92, 1.1, 2.1, "DI", 12),
    ("PP2", "P1", "T1", 350, 78, 1.3, 3.4, "DI", 12),
    ("PP3", "P1", "J1", 300, 44, 1.0, 2.8, "PVC", 18),
    ("PP4", "T1", "J2", 300, 55, 1.2, 2.5, "PVC", 8),
    ("PP5", "J2", "P2", 300, 48, 1.1, 3.0, "HDPE", 5),
    ("PP6", "P2", "T2", 350, 62, 1.4, 3.2, "DI", 15),
    ("PP7", "P2", "V1", 250, 28, 0.9, 2.1, "PVC", 22),
    ("PP8", "V1", "J1", 250, 25, 0.8, 1.8, "PVC", 22),
    ("PP9", "V1", "C2", 200, 31, 1.0, 4.1, "HDPE", 6),
    ("PP10", "T2", "J3", 300, 40, 1.1, 2.4, "DI", 15),
    ("PP11", "J3", "P3", 250, 22, 0.7, 2.9, "Steel", 32),
    ("PP12", "P3", "V2", 250, 20, 0.6, 2.2, "Steel", 32),
    ("PP13", "V2", "C3", 200, 19, 0.8, 3.4, "PVC", 14),
    ("PP14", "P3", "C4", 200, 15, 0.7, 4.6, "Steel", 32),
    ("PP15", "J1", "J4", 250, 26, 0.9, 2.6, "PVC", 18),
    ("PP16", "J4", "C1", 200, 24, 0.9, 3.8, "PVC", 20),
]


async def run():
    async with AsyncSessionLocal() as db:
        u = (
            await db.execute(select(User).where(User.email == "demo@aquaflow.io"))
        ).scalar_one_or_none()
        if not u:
            u = User(
                email="demo@aquaflow.io",
                hashed_password=hash_password("demo1234"),
                role="admin",
                updated_at=datetime.now(timezone.utc),
            )
            db.add(u)
            await db.flush()
        net = (
            await db.execute(select(Network).where(Network.name == "Default"))
        ).scalar_one_or_none()
        if net:
            print("Already seeded.")
            return
        net = Network(
            name="Default", owner_id=u.id, updated_at=datetime.now(timezone.utc)
        )
        db.add(net)
        await db.flush()
        for r in NODES:
            db.add(
                Node(
                    network_id=net.id,
                    ext_id=r[0],
                    type=r[1],
                    label=r[2],
                    x=r[3],
                    y=r[4],
                    pressure=r[5],
                    demand=r[6],
                    level=r[7],
                    rated_kw=r[8],
                    elevation=r[9],
                    leak_prob=r[10],
                    status=r[11],
                    updated_at=datetime.now(timezone.utc),
                )
            )
        for r in PIPES:
            db.add(
                Pipe(
                    network_id=net.id,
                    ext_id=r[0],
                    from_ext=r[1],
                    to_ext=r[2],
                    diameter=r[3],
                    flow=r[4],
                    velocity=r[5],
                    headloss=r[6],
                    material=r[7],
                    age=r[8],
                    updated_at=datetime.now(timezone.utc),
                )
            )
        await db.commit()
        print(f"Seeded network #{net.id} with {len(NODES)} nodes + {len(PIPES)} pipes.")
        print("Login: demo@aquaflow.io / demo1234")


if __name__ == "__main__":
    asyncio.run(run())
