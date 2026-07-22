"""ML inference for leak detection, demand forecasting, pump optimization.

Loads sklearn artifacts from app/ml/artifacts/ when present; falls back to
deterministic heuristics so the API works without training.
"""

from __future__ import annotations
import math, os, json
from pathlib import Path
from typing import Iterable
import numpy as np

ART = Path(__file__).parent / "artifacts"
ART.mkdir(exist_ok=True)


# ---------- Leak detection ----------
def _material_risk(m: str) -> float:
    return {"PVC": 0.10, "HDPE": 0.05, "DI": 0.15, "Steel": 0.30}.get(m, 0.15)


def leak_probability(node, incident_pipes, pressure_residual: float) -> float:
    """Heuristic + optional IsolationForest."""
    model_path = ART / "leak_iforest.joblib"
    if model_path.exists():
        try:
            import joblib

            m = joblib.load(model_path)
            feats = np.array(
                [
                    [
                        pressure_residual,
                        (
                            np.mean([p.age for p in incident_pipes])
                            if incident_pipes
                            else 0
                        ),
                        (
                            np.mean(
                                [_material_risk(p.material) for p in incident_pipes]
                            )
                            if incident_pipes
                            else 0
                        ),
                    ]
                ]
            )
            s = -m.score_samples(feats)[0]
            return float(1 / (1 + math.exp(-2.0 * (s - 0.5))))
        except Exception:
            pass
    age_score = (
        np.mean([min(p.age, 40) / 40 for p in incident_pipes])
        if incident_pipes
        else 0.2
    )
    mat_score = (
        np.mean([_material_risk(p.material) for p in incident_pipes])
        if incident_pipes
        else 0.15
    )
    pr = min(abs(pressure_residual) / 8.0, 1.0)
    raw = 0.55 * pr + 0.25 * age_score + 0.20 * mat_score
    return float(1 / (1 + math.exp(-6 * (raw - 0.45))))


# ---------- Demand forecast ----------
def forecast_hourly(base_ml_per_h: float, hours: int = 24) -> list[dict]:
    model_path = ART / "demand_linreg.joblib"
    coefs = None
    if model_path.exists():
        try:
            import joblib

            coefs = joblib.load(model_path)  # dict with hour-of-day coefs
        except Exception:
            coefs = None
    out = []
    for h in range(hours):
        seasonal = 1 + 0.35 * math.sin((h - 7) / 24 * math.pi * 2)
        morning = 0.25 if 7 <= h <= 9 else 0
        evening = 0.30 if 18 <= h <= 21 else 0
        mult = coefs["hourly"][h] if coefs else seasonal + morning + evening
        fc = base_ml_per_h * mult
        band = 0.08 * fc
        out.append(
            {
                "t": f"{h:02d}:00",
                "forecast": round(fc, 2),
                "lower": round(fc - band, 2),
                "upper": round(fc + band, 2),
                "actual": None,
            }
        )
    return out


# ---------- Pump schedule optimization ----------
def default_tariff(h: int) -> float:
    if h >= 22 or h < 6:
        return 6.0
    if 17 <= h <= 21:
        return 24.0
    return 14.0


def optimize_pump_schedule(
    pumps: list[dict], tariff: list[float] | None = None
) -> dict:
    """Duty proportional to 1/tariff^1.4; baseline is flat 65% duty."""
    tariff = tariff or [default_tariff(h) for h in range(24)]
    total_kw = sum(p.get("rated_kw") or 0 for p in pumps) or 1.0
    weights = np.array([1 / (t**1.4) for t in tariff])
    weights = weights / weights.sum()
    target_energy_kwh = total_kw * 0.65 * 24  # baseline duty daily
    duties = weights * 24  # per-hour duty fraction sum equals 24 * mean
    # scale duties so mean matches baseline mean 0.65
    duties = duties * (0.65 / duties.mean())
    duties = np.clip(duties, 0.15, 1.0)
    schedule = []
    kwh = 0.0
    cost = 0.0
    for h in range(24):
        kw = total_kw * duties[h]
        kwh += kw
        cost += kw * tariff[h] / 100  # cents -> dollars
        schedule.append(
            {
                "hour": h,
                "tariff": tariff[h],
                "pump_kw": round(kw, 1),
                "duty": round(float(duties[h]), 3),
            }
        )
    baseline_cost = sum(total_kw * 0.65 * tariff[h] / 100 for h in range(24))
    return {
        "schedule": schedule,
        "daily_kwh": round(kwh, 1),
        "daily_cost": round(cost, 2),
        "baseline_cost": round(baseline_cost, 2),
        "savings": round(baseline_cost - cost, 2),
        "co2_kg": round(kwh * 0.38, 1),
    }
