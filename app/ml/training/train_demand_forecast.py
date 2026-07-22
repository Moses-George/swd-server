"""Train a per-hour multiplicative demand profile.

Real data sources:
- BattLeDIM demand CSVs (per DMA, 5-min).
- Any utility SCADA dump with columns: timestamp, demand_ml_h.
- Optionally join with NOAA hourly weather (ncei.noaa.gov) for temperature effects.

Run:  python -m app.ml.training.train_demand_forecast
"""
import pandas as pd, numpy as np, joblib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "demand.csv"
OUT = ROOT / "app" / "ml" / "artifacts" / "demand_linreg.joblib"


def main():
    if not DATA.exists():
        raise SystemExit(f"Place demand.csv at {DATA} (columns: timestamp, demand)")
    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    hourly = df.groupby("hour")["demand"].mean()
    hourly = hourly / hourly.mean()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"hourly": hourly.reindex(range(24)).ffill().values.tolist()}, OUT)
    print(f"Saved {OUT} — mean-normalized 24h profile")


if __name__ == "__main__":
    main()
