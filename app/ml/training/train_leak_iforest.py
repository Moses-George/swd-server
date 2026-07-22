"""Train IsolationForest on BattLeDIM pressure residuals.

Data: https://zenodo.org/record/4017659   (L-Town dataset)
Extract to data/battledim/ then run:  python -m app.ml.training.train_leak_iforest
"""

import pandas as pd, numpy as np, joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "battledim"
OUT = ROOT / "app" / "ml" / "artifacts" / "leak_iforest.joblib"


def build_features(pressure_df: pd.DataFrame, pipe_meta: pd.DataFrame) -> pd.DataFrame:
    # residual = obs - rolling median (naive baseline replacement for EPANET)
    resid = pressure_df - pressure_df.rolling(48, min_periods=6).median()
    feats = pd.DataFrame(
        {
            "residual": resid.stack().values,
            "age": np.tile(pipe_meta["age"].mean(), len(resid) * pressure_df.shape[1]),
            "mat_risk": np.tile(
                pipe_meta["mat_risk"].mean(), len(resid) * pressure_df.shape[1]
            ),
        }
    ).dropna()
    return feats


def main():
    if not DATA.exists():
        raise SystemExit(f"Place BattLeDIM CSVs under {DATA}")
    p = pd.read_csv(
        DATA / "pressures.csv", parse_dates=["timestamp"], index_col="timestamp"
    )
    meta = pd.read_csv(DATA / "pipe_meta.csv")
    X = build_features(p, meta).values
    model = IsolationForest(n_estimators=300, contamination=0.02, random_state=0).fit(X)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
