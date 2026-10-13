"""
Weather-only test and scheduling-loop sensitivity with the trained actors
(no retraining).

    python -m vsg_rl.sensitivity --out results_measured_final

The load contingencies are switched off, so only the measured irradiance and
wind disturb the frequency, and the time constant of the BESS scheduling loop
(TAU_AGC, tau_sch in the paper) is varied.  A slower loop lets more of the
measured variability reach the frequency.  Best (validation-selected) actors
of every seed, and the tuned baselines, are evaluated on the five test
windows and the 50 held-out stress windows.
"""
import argparse
import json
import os

import numpy as np

from . import config as C
from .utils import mean_ci95

CTRL = ["none", "fixed_tuned", "adaptive_rule", "ddpg", "td3"]
METRICS = [("iae", "IAE (Hz·s)", "{:.3f}"), ("df_max_hz", "max |Δf| (Hz)", "{:.3f}"),
           ("rocof_win", "RoCoF (Hz/s)", "{:.3f}"), ("reserve_pu", "Reserve (pu)", "{:.3f}")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results_measured_final")
    ap.add_argument("--seeds", default=",".join(str(s) for s in range(10)))
    ap.add_argument("--taus", default="1,10,30")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    C.WEATHER_SOURCE, C.OUT_DIR = "measured", args.out
    seeds = [int(s) for s in args.seeds.split(",")]
    from . import evaluate as E
    from .baselines import make_policy
    from .train import load_agent
    with open(os.path.join(args.out, "tuned_baselines.json")) as fh:
        tuned = json.load(fh)
    pols = {(c, None): make_policy(c, tuned=tuned) for c in CTRL[:3]}
    for a in ("ddpg", "td3"):
        for s in seeds:
            ag, _ = load_agent(a, s)
            pols[(a, s)] = ag.policy()

    # weather only: no load contingencies in any episode
    C.LOAD_STEP = {k: 0.0 for k in C.LOAD_STEP}
    C.RAND_STEP_FRAC = (0.0, 0.0)
    res = {}
    for tau in [float(t) for t in args.taus.split(",")]:
        C.TAU_AGC = tau
        for split, eps in (("test", E.test_episodes()), ("stress", E.stress_episodes())):
            per = E.evaluate_many(pols, eps, workers=args.workers)
            res[(tau, split)] = {c: [E.episode_mean(r) for (cc, s), r in per.items() if cc == c]
                                 for c in CTRL}
            print(f"tau_sch {tau:g} s, {split}: done", flush=True)

    L = ["# Weather-only test and scheduling-loop sensitivity (trained actors, no retraining)\n",
         "Load contingencies switched off; only measured irradiance and wind disturb the frequency. "
         "tau_sch = time constant of the BESS scheduling loop (TAU_AGC, 1 s in all other results). "
         "RL: best actors, mean ± 95 % CI over seeds.\n"]
    for split, title in (("stress", "50 held-out stress windows"), ("test", "Five test windows")):
        L.append(f"## {title}\n")
        L.append("| tau_sch (s) | Controller | " + " | ".join(h for _, h, _ in METRICS) + " |")
        L.append("|---|---|" + "---|" * len(METRICS))
        for tau in [float(t) for t in args.taus.split(",")]:
            for c in CTRL:
                rows = res[(tau, split)][c]
                cells = []
                for m, _, f in METRICS:
                    mu, _, ci = mean_ci95([r[m] for r in rows])
                    cells.append(f.format(mu) + (f" ± {f.format(ci)}" if len(rows) > 1 else ""))
                L.append(f"| {tau:g} | {C.CONTROLLER_LABELS[c]} | " + " | ".join(cells) + " |")
        L.append("")
    path = os.path.join(args.out, "SENSITIVITY_weather_only.md")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
