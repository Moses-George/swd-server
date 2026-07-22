"""Scenario transforms and metric computation. Pure functions over ORM
instances — returns new lightweight dicts, does not mutate the DB."""

from copy import deepcopy


def _clone(nodes, pipes):
    def d(x):
        return {c.name: getattr(x, c.name) for c in x.__table__.columns}

    return [d(n) for n in nodes], [d(p) for p in pipes]


def apply_scenario(nodes, pipes, kind: str, params: dict):
    ns, ps = _clone(nodes, pipes)
    if kind == "pop":
        factor = 1 + float(params.get("growth", 0.15))
        for n in ns:
            if n["type"] == "consumer" and n.get("demand"):
                n["demand"] = round(n["demand"] * factor, 2)
                n["pressure"] = max(10, n["pressure"] - 4)
    elif kind == "pump":
        target = params.get("pump_ext")
        for n in ns:
            if n["type"] == "pump" and (target is None or n["ext_id"] == target):
                n["status"] = "alert"
                n["rated_kw"] = 0
                n["pressure"] = max(5, n["pressure"] - 15)
    elif kind == "burst":
        target = params.get("pipe_ext")
        for p in ps:
            if target is None or p["ext_id"] == target:
                p["flow"] = p["flow"] * 2.5
                p["headloss"] = p["headloss"] * 3
                break
    elif kind == "res":
        ns.append(
            {
                "id": None,
                "network_id": nodes[0].network_id if nodes else None,
                "ext_id": f"R{len([n for n in ns if n['type']=='reservoir'])+1}",
                "type": "reservoir",
                "label": params.get("name", "New Reservoir"),
                "x": float(params.get("x", 90)),
                "y": float(params.get("y", 10)),
                "pressure": 60,
                "demand": None,
                "level": None,
                "rated_kw": None,
                "elevation": 30,
                "leak_prob": 0,
                "status": "ok",
            }
        )
    elif kind == "solar":
        # No topology change; energy cost effect handled in metrics
        pass
    return ns, ps


def network_metrics(nodes, pipes) -> dict:
    # Accept either ORM or dicts
    def g(x, k):
        return x.get(k) if isinstance(x, dict) else getattr(x, k, None)

    consumers = [n for n in nodes if g(n, "type") == "consumer"]
    pumps = [n for n in nodes if g(n, "type") == "pump"]
    pressures = [
        g(n, "pressure") or 0 for n in nodes if g(n, "type") in ("consumer", "junction")
    ]
    demand_ls = sum((g(c, "demand") or 0) for c in consumers)
    peak_demand_mlh = round(demand_ls * 3.6 / 1000 * 1.45, 2)
    energy_kwh = round(sum((g(p, "rated_kw") or 0) for p in pumps) * 0.65 * 24, 1)
    return {
        "peak_demand_mlh": peak_demand_mlh,
        "min_pressure_m": round(min(pressures) if pressures else 0, 1),
        "avg_pressure_m": round(sum(pressures) / len(pressures), 1) if pressures else 0,
        "energy_kwh_day": energy_kwh,
        "co2_kg_day": round(energy_kwh * 0.38, 1),
        "node_count": len(nodes),
        "pipe_count": len(pipes),
    }
