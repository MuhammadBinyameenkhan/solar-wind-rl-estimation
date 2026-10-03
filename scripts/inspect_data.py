"""Show how your raw ERA5 and NASA POWER CSVs are parsed (columns, units, time span)."""
import pandas as pd
from _common import base_parser, setup

from vsgrl.config import resolve_path
from vsgrl.data import era5, nasa_power

if __name__ == "__main__":
    a = base_parser(__doc__).parse_args()
    cfg = setup(a)
    d = cfg["data"]
    p = resolve_path(d["era5_csv"])
    print(f"\n=== ERA5: {p}")
    raw = pd.read_csv(p, comment="#", nrows=5)
    print("columns:", list(raw.columns))
    print("detected:", {k: v for k, v in era5.detect_columns(raw, d.get("era5_columns") or {}).items() if v})
    w = era5.load_era5_csv(p, d.get("era5_columns") or {}, cfg["site"]["latitude"], cfg["site"]["longitude"],
                           cfg["system"]["wind"]["hub_height_m"], cfg["system"]["wind"]["shear_exponent"])
    print(w.describe().T[["mean", "min", "max"]])
    print("span:", w.index.min(), "→", w.index.max(), f"({len(w)} h)")

    p = resolve_path(d["nasa_power_csv"])
    print(f"\n=== NASA POWER: {p}")
    s = nasa_power.load_nasa_power_csv(p, d.get("nasa_columns") or {}, d["nasa_time_standard"],
                                       d["nasa_utc_offset_hours"])
    print("header metadata:", s.attrs)
    print(s.describe().T[["mean", "min", "max"]])
    print("span:", s.index.min(), "→", s.index.max(), f"({len(s)} h)")
    print("\nOverlap:", len(w.index.intersection(s.index)), "hours")
