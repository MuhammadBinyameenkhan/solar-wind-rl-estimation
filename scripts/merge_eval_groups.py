"""Merge evaluation runs made in parallel into one results folder.

Each group was run with --set eval.out_dir=results_gN. The groups must have used the same
test scenarios (checked here); their per_scenario.csv files and traces are combined into the
configured eval.out_dir (default results/).
Usage: python scripts/merge_eval_groups.py results_g1 results_g2 results_g3 results_g4
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base_parser, setup  # noqa: E402

from vsgrl.config import resolve_path  # noqa: E402

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("groups", nargs="+")
    a = p.parse_args()
    cfg = setup(a)
    out = resolve_path(cfg["eval"]["out_dir"])
    (out / "traces").mkdir(parents=True, exist_ok=True)
    dirs = [resolve_path(g) for g in a.groups]

    ref = pd.read_csv(dirs[0] / "scenarios_test.csv")
    for d in dirs[1:]:
        other = pd.read_csv(d / "scenarios_test.csv")
        if not ref.equals(other):
            sys.exit(f"scenarios differ between {dirs[0]} and {d}: not merging")
    shutil.copy(dirs[0] / "scenarios_test.csv", out / "scenarios_test.csv")

    frames = [pd.read_csv(d / "per_scenario.csv") for d in dirs]
    res = pd.concat(frames, ignore_index=True)
    dup = res.duplicated(["controller", "seed", "scenario"]).sum()
    if dup:
        sys.exit(f"{dup} duplicated (controller, seed, scenario) rows: groups overlap")
    res.to_csv(out / "per_scenario.csv", index=False)
    n_tr = 0
    for d in dirs:
        for f in (d / "traces").glob("*.csv"):
            shutil.copy(f, out / "traces" / f.name)
            n_tr += 1
    summary = res.groupby("controller").agg(runs=("seed", "nunique"), scenarios=("scenario", "nunique"))
    print(summary.to_string())
    print(f"merged {len(res)} rows and {n_tr} traces into {out}")
