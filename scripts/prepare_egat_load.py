"""Convert EGAT hourly regional demand (2024) into the microgrid load file read by vsgrl.

The EGAT data give the Northeast-region demand in MW (thousands of MW). The microgrid
uses its *shape*: daily, weekly and seasonal variation, holidays and weather-driven
cooling load. Two scalings are available:

  peak   (default)  load = P_peak · d(t) / max d          keeps the measured load factor
  minmax            load = P_min + (P_peak − P_min) · (d − min d)/(max d − min d)

Peak scaling is the default because it preserves the ratio between low and high demand
that was actually measured; min–max stretches the variation to fill the given band.

Usage:
  python scripts/prepare_egat_load.py --input data/raw/egat_2024.csv
         [--region-col northeast_demand] [--time-col datetime] [--tz-offset 7]
         [--scaling peak|minmax] [--peak-mw 0.8] [--min-mw 0.3]
         [--output data/raw/egat_northeast_2024_load.csv]
Then set data.load_csv in configs/default.yaml to the output file.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TIME_HINTS = ("datetime", "date_time", "timestamp", "time", "date")
REGION_HINTS = ("northeast", "north_east", "ne_", "isan")


def pick(columns, hints, what, exclude=()):
    low = {c.lower(): c for c in columns}
    for h in hints:
        hits = [c for lc, c in low.items() if h in lc and c not in exclude]
        if hits:
            return hits[0]
    sys.exit(f"Could not find the {what} column; pass it explicitly. Columns: {list(columns)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="data/raw/egat_northeast_2024_load.csv")
    ap.add_argument("--time-col")
    ap.add_argument("--region-col")
    ap.add_argument("--tz-offset", type=float, default=7.0, help="hours of the timestamps ahead of UTC (Thailand: 7)")
    ap.add_argument("--scaling", choices=["peak", "minmax"], default="peak")
    ap.add_argument("--peak-mw", type=float, default=0.8)
    ap.add_argument("--min-mw", type=float, default=0.3)
    ap.add_argument("--year", type=int, default=2024)
    a = ap.parse_args()

    df = pd.read_csv(a.input)
    tcol = a.time_col or pick(df.columns, TIME_HINTS, "time")
    rcol = a.region_col or pick(df.columns, REGION_HINTS, "Northeast demand", exclude=(tcol,))
    print(f"time column: {tcol!r}; demand column: {rcol!r}")

    t = pd.to_datetime(df[tcol])
    if t.dt.tz is None:
        t = (t - pd.Timedelta(hours=a.tz_offset)).dt.tz_localize("UTC")
    else:
        t = t.dt.tz_convert("UTC")
    d = pd.Series(pd.to_numeric(df[rcol], errors="coerce").to_numpy(), index=t).sort_index()
    d = d[~d.index.duplicated(keep="first")]
    d = d[(d.index >= pd.Timestamp(f"{a.year}-01-01", tz="UTC"))
          & (d.index < pd.Timestamp(f"{a.year + 1}-01-01", tz="UTC"))]   # same UTC year as ERA5 / NASA POWER
    hourly = d.resample("1h").mean()
    n_missing = int(hourly.isna().sum())
    filled = hourly.interpolate(limit=6)
    n_unfilled = int(filled.isna().sum())

    if a.scaling == "peak":
        load = a.peak_mw * filled / filled.max()
    else:
        load = a.min_mw + (a.peak_mw - a.min_mw) * (filled - filled.min()) / (filled.max() - filled.min())

    out = pd.DataFrame({"time": load.index.strftime("%Y-%m-%dT%H:%M:%SZ"), "load_mw": load.to_numpy()}).dropna()
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.output, index=False)

    local = load.index + pd.Timedelta(hours=a.tz_offset)
    prof = load.groupby(local.hour).mean()
    print(f"rows {len(out)}; hours missing in source {n_missing}, left unfilled {n_unfilled}")
    print(f"source demand: min {filled.min():.0f}, mean {filled.mean():.0f}, max {filled.max():.0f} (units of the file)")
    print(f"scaled load ({a.scaling}): min {load.min():.3f}, mean {load.mean():.3f}, max {load.max():.3f} MW; "
          f"load factor {load.mean() / load.max():.3f}")
    print(f"daily shape (local time): low at {int(prof.idxmin()):02d}:00 ({prof.min():.3f} MW), "
          f"peak at {int(prof.idxmax()):02d}:00 ({prof.max():.3f} MW)")
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
