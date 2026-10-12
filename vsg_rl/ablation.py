"""
Ablation of the RL fixes: which change helps and which hurts regulation.

    python -m vsg_rl.ablation --seeds 0,1,2 --episodes 500 --workers 4

Every variant starts from the corrected base A (the original setup with the
weight-decay bug fixed) and adds ONE group of changes.  ALL is the full
fixed setup of results_measured_v2.  Both algorithms, same seeds, same
episodes; the TD3-only smoothing (sigma 0.1, clip 0.3) and the small
pre-tanh L2 are present in every variant.  All training jobs of all variants
share one process pool, then each variant's best actors are evaluated on the
five test scenarios and the 50-episode stress test.
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import config as C
from .utils import log, mean_ci95, welch_t

# The original (pre-fix) values of every switch, except weight decay.
OLD = dict(ROCOF_REWARD_WINDOW=False, W_ROCOF=10.0, W_ROCOF_HINGE=0.0, W_RATE=0.0,
           ACTION_FILTER_TAU=0.0, OBS_NORM=False, REWARD_SCALE=1.0, REWARD_SHIFT=False,
           ROCOF_STRESS_PROB=(0.0, 0.0, 0.0), ADAM_EPS=1e-8, PER_EPS=1e-5)
# The full results_measured_v2 setup (pinned: the defaults later changed to
# the configuration this ablation selected).
NEW = dict(ROCOF_REWARD_WINDOW=True, W_ROCOF=25.0, W_ROCOF_HINGE=20.0, W_RATE=0.05,
           ACTION_FILTER_TAU=0.08, OBS_NORM=True, REWARD_SCALE=1e-3, REWARD_SHIFT=True,
           ROCOF_STRESS_PROB=(0.0, 0.15, 0.30), ADAM_EPS=1e-10, PER_EPS=1e-6)


def _with(*keys):
    return {**OLD, **{k: NEW[k] for k in keys}}


VARIANTS = {
    "A_base":        (dict(OLD), "original setup + weight-decay fix"),
    "B_relay_rocof": (_with("ROCOF_REWARD_WINDOW", "W_ROCOF", "W_ROCOF_HINGE"),
                      "A + RoCoF reward from the 500 ms relay window (w 25, hinge 20)"),
    "C_smoothing":   (_with("ACTION_FILTER_TAU", "W_RATE"),
                      "A + actuator low-pass (0.08 s) + action-rate penalty"),
    "D_obs_norm":    (_with("OBS_NORM"), "A + running observation normalisation"),
    "E_reward_scale": (_with("REWARD_SCALE", "REWARD_SHIFT", "ADAM_EPS", "PER_EPS"),
                       "A + learner reward scaled to [-12, 0] (Adam eps 1e-10)"),
    "F_rocof_stress": (_with("ROCOF_STRESS_PROB"), "A + RoCoF-stress training episodes"),
    "ALL":           (dict(NEW), "every change (the results_measured_v2 setup)"),
}

REPORT = [("iae", "IAE (Hz·s)", "{:.3f}"), ("ise", "ISE", "{:.3f}"),
          ("nadir_hz", "Nadir (Hz)", "{:.3f}"), ("rocof_win", "RoCoF (Hz/s)", "{:.3f}"),
          ("reserve_pu", "Reserve (pu)", "{:.3f}"), ("bound_pct", "At bounds (%)", "{:.1f}"),
          ("dJ_quiet", "|ΔJ| quiet (s/step)", "{:.3f}"), ("dD_quiet", "|ΔD| quiet (pu/step)", "{:.3f}"),
          ("J_release_spike", "J release spike (s)", "{:.2f}")]


def apply(variant: str) -> None:
    for k, v in VARIANTS[variant][0].items():
        setattr(C, k, v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--episodes", type=int, default=500)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="results_ablation")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--stage", choices=["all", "evaluate"], default="all")
    args = ap.parse_args(argv)
    seeds = [int(s) for s in args.seeds.split(",")]
    variants = args.variants.split(",")
    C.WEATHER_SOURCE = "measured"
    C.EPISODES = args.episodes
    os.makedirs(args.out, exist_ok=True)
    C.OUT_DIR = args.out

    from . import evaluate as E
    from .train import _worker, config_overrides, load_agent

    t0 = time.time()
    if args.stage == "all":
        jobs = []
        for s in seeds:                       # interleave variants: even progress
            for v in variants:
                for a in ("ddpg", "td3"):
                    apply(v)
                    C.OUT_DIR = os.path.join(args.out, v)
                    jobs.append((a, s, args.episodes, None, True, config_overrides()))
        log(f"[ablation] {len(jobs)} training jobs, {args.workers} workers")
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for a, s in ex.map(_worker, jobs):
                log(f"[ablation] finished {a} seed {s}  ({time.time() - t0:.0f}s)")

    results = {}
    for v in variants:
        apply(v)
        C.OUT_DIR = os.path.join(args.out, v)
        pols, hists = {}, {}
        for a in ("ddpg", "td3"):
            for s in seeds:
                ag, h = load_agent(a, s)
                if ag is not None:
                    pols[(a, s)], hists[(a, s)] = ag.policy(), h
        log(f"[ablation] evaluating {v}: {len(pols)} actors")
        test = E.evaluate_many(pols, E.test_episodes(), workers=args.workers)
        stress = E.evaluate_many(pols, E.stress_episodes(), workers=args.workers)
        res = {}
        for a in ("ddpg", "td3"):
            ks = [k for k in pols if k[0] == a]
            res[a] = {
                "test": {m: [E.episode_mean(test[k])[m] for k in ks] for m, _, _ in REPORT},
                "stress": {m: [E.episode_mean(stress[k])[m] for k in ks] for m, _, _ in REPORT},
                "best_ep": [hists[k].get("best_episode") for k in ks],
                "bias": [hists[k]["q_bias"][hists[k]["eval_ep"].index(hists[k]["best_episode"])]
                         for k in ks],
            }
        results[v] = res
        with open(os.path.join(args.out, "ablation_results.json"), "w") as fh:
            json.dump(results, fh, indent=1, default=float)
    write_report(results, variants, seeds, args)
    log(f"[ablation] COMPLETE in {time.time() - t0:.0f}s")


def write_report(results, variants, seeds, args):
    L = ["# Ablation of the RL fixes\n",
         f"Seeds {seeds}, {args.episodes} episodes per run, best (validation-selected) actors. "
         "Mean ± 95 % CI over seeds. Δ = change of the stress-test IAE against A_base, "
         "t = Welch t on the per-seed values.\n"]
    for v in variants:
        L.append(f"* **{v}** — {VARIANTS[v][1]}")
    L.append("")
    for split in ("stress", "test"):
        L.append(f"## {'Held-out stress test (50 episodes)' if split == 'stress' else 'Five test scenarios'}\n")
        for a in ("td3", "ddpg"):
            L.append(f"### {a.upper()}\n")
            L.append("| Variant | " + " | ".join(h for _, h, _ in REPORT) + " | ΔIAE vs A | t |")
            L.append("|---|" + "---|" * (len(REPORT) + 2))
            base = results.get("A_base", {}).get(a, {}).get(split, {}).get("iae")
            for v in variants:
                r = results[v][a][split]
                cells = []
                for m, _, f in REPORT:
                    x = np.asarray(r[m], dtype=float)
                    x = x[~np.isnan(x)]
                    mu, _, ci = mean_ci95(x) if len(x) else (np.nan, 0, np.nan)
                    cells.append(f"{f.format(mu)} ± {f.format(ci)}")
                if base is not None and v != "A_base":
                    d = 100 * (np.mean(r["iae"]) / np.mean(base) - 1)
                    t = welch_t(r["iae"], base)[0]
                    tail = f"{d:+.1f} % | {t:+.2f}"
                else:
                    tail = "– | –"
                L.append(f"| {v} | " + " | ".join(cells) + f" | {tail} |")
            L.append("")
    L.append("## Model selection and critic bias (validation states, learner units of each variant)\n")
    L.append("| Variant | DDPG best episodes | DDPG Q − G | TD3 best episodes | TD3 Q − G |")
    L.append("|---|---|---|---|---|")
    for v in variants:
        d, t = results[v]["ddpg"], results[v]["td3"]
        L.append(f"| {v} | {d['best_ep']} | {np.mean(d['bias']):+.3g} | "
                 f"{t['best_ep']} | {np.mean(t['bias']):+.3g} |")
    with open(os.path.join(args.out, "RESULTS.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    log("\n".join(L))


if __name__ == "__main__":
    main()
