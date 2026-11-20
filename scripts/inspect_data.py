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
    if not str(p).endswith(".nc"):
        raw = pd.read_csv(p, comment="#", nrows=5)
        print("columns:", list(raw.columns))
        print("detected:", {k: v for k, v in era5.detect_columns(raw, d.get("era5_columns") or {}).items() if v})
    hdr = nasa_power.parse_header(open(resolve_path(d["nasa_power_csv"])).read().split("-END HEADER-")[0])
    lat = cfg["site"]["latitude"] or hdr.get("latitude")
    lon = cfg["site"]["longitude"] or hdr.get("longitude")
    w = era5.load_era5(p, d.get("era5_columns") or {}, lat, lon,
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
    off = cfg["site"].get("utc_offset_hours") or (s.attrs.get("longitude", 0) / 15)
    noon = (s.groupby(((s.index.hour + off) % 24).astype(int)).ghi_wm2.mean()).idxmax()
    print(f"GHI peaks at local hour {noon} (should be 11-13)")
    print("\nOverlap:", len(w.index.intersection(s.index)), "hours")
