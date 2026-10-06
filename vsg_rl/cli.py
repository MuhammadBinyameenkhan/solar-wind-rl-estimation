"""
Command-line entry point.

    python -m vsg_rl                         full study: 5 seeds x {DDPG, TD3}
    python -m vsg_rl --seeds 0,1,2 --workers 3
    python -m vsg_rl --smoke                 ~2 min end-to-end pipeline check
    python -m vsg_rl --stage evaluate        re-evaluate trained checkpoints
    python -m vsg_rl --stage figures         re-plot from saved results
    python -m vsg_rl --fresh                 discard checkpoints and caches
"""
import argparse
import json
import os
import shutil
import time

import numpy as np

from . import config as C
from .utils import log, reset_log, set_global_seed


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="RL-VSG microgrid study (DDPG vs TD3)")
    ap.add_argument("--seeds", default=",".join(map(str, C.DEFAULT_SEEDS)),
                    help="comma-separated training seeds (default 0,1,2,3,4)")
    ap.add_argument("--algos", default="ddpg,td3")
    ap.add_argument("--episodes", type=int, default=C.EPISODES)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 1)),
                    help="parallel processes for training and evaluation")
    ap.add_argument("--stage", choices=["all", "train", "evaluate", "figures"], default="all")
    ap.add_argument("--n-stress", type=int, default=C.N_STRESS)
    ap.add_argument("--weather", choices=["calibrated", "synthetic"], default=C.WEATHER_SOURCE)
    ap.add_argument("--hz", type=float, default=None)
    ap.add_argument("--out", default=None, help="output directory (default results/)")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-panels", action="store_true")
    return ap.parse_args(argv)


def apply_args(args):
    if args.out:
        C.OUT_DIR = args.out
    if args.hz:
        C.set_nominal_frequency(args.hz)
    C.WEATHER_SOURCE = args.weather
    C.EPISODES = args.episodes
    C.N_STRESS = args.n_stress
    C.SAVE_PANELS = not args.no_panels
    if args.smoke:
        C.OUT_DIR = args.out or os.path.join("results", "smoke")
        C.EPISODES = 6
        C.EVAL_EVERY = 3
        C.WARMUP_STEPS = 300
        C.N_VAL = 2
        C.N_STRESS = 5
        C.EPISODE_DURATION = 10.0
        C.FIXED_GRID_J = [0.0, 1.0]
        C.FIXED_GRID_D = [10.0, 30.0]
        C.FIXED_GRID_KQ = [8.0, 20.0]
        from . import baselines
        baselines.RULE_GRID = dict(J0=[0.5], kJ=[0.0, 5.0], D0=[20.0], kD=[40.0], Kq=[8.0, 20.0])
        args.seeds = "0,1"


def representative_seed(hists: dict):
    """Seed whose best validation return is the median (for time traces)."""
    vals = sorted((h.get("best_val_return", -np.inf), s) for s, h in hists.items())
    return vals[len(vals) // 2][1]


def main(argv=None):
    args = parse_args(argv)
    apply_args(args)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    algos = [a.strip() for a in args.algos.split(",") if a.strip()]

    if args.fresh and os.path.isdir(C.OUT_DIR):
        shutil.rmtree(C.OUT_DIR)
    os.makedirs(C.OUT_DIR, exist_ok=True)
    if args.stage in ("all", "train"):
        reset_log()
    set_global_seed(C.SEED)

    import torch
    from . import evaluate as E
    from .baselines import FixedPolicy, make_policy, tune_baselines
    from .env import MicrogridVSGEnv
    from .train import load_agent, train_many

    t0 = time.time()
    log("=" * 72)
    log("  RL-BASED VSG CONTROL — DDPG vs TD3 — solar/wind/BESS microgrid")
    log(f"  seeds {seeds} | algos {algos} | episodes {C.EPISODES} x "
        f"{C.max_steps()} steps | weather {C.WEATHER_SOURCE} | {C.F_NOM:.0f} Hz")
    log(f"  PyTorch {torch.__version__} | workers {args.workers}")
    log("=" * 72)

    # 1 -- tune the non-learning baselines on the validation set
    tuned = tune_baselines(workers=args.workers, fresh=args.fresh)

    # 2 -- train every (algo, seed)
    if args.stage in ("all", "train"):
        train_many(algos, seeds, episodes=C.EPISODES, resume=not args.fresh,
                   workers=args.workers)
        if args.stage == "train":
            return 0

    agents, hists = {}, {a: {} for a in algos}
    for a in algos:
        for s in seeds:
            ag, h = load_agent(a, s)
            if ag is not None:
                agents[(a, s)], hists[a][s] = ag, h
    if not agents:
        log("No trained agents found — run with --stage all or train first.")
        return 1

    tdir = E.tables_dir()
    baseline_names = [c for c in C.CONTROLLERS if c not in ("ddpg", "td3")]
    order = baseline_names + [a for a in algos]

    # 3 -- evaluation on the test scenarios and the held-out stress test
    res_path = os.path.join(C.OUT_DIR, "eval_cache.pt")
    if args.stage in ("all", "evaluate") or not os.path.exists(res_path):
        policies = {(c, None): make_policy(c, tuned=tuned) for c in baseline_names}
        policies.update({(a, s): ag.policy() for (a, s), ag in agents.items()})
        log(f"\n[evaluate] {len(policies)} controllers x {len(C.EVAL_SCENARIOS)} test scenarios ...")
        test = E.evaluate_many(policies, E.test_episodes(), workers=args.workers)
        log(f"[evaluate] held-out stress test: {C.N_STRESS} randomised episodes each ...")
        stress = E.evaluate_many(policies, E.stress_episodes(), workers=args.workers)
        log("[evaluate] fixed-gain grid on the test scenarios (Pareto frontier) ...")
        grid_pol = {(f"J{J}_D{D}", None): FixedPolicy(J, D)
                    for J in np.arange(0.0, 4.01, 0.5) for D in np.arange(5.0, 60.1, 5.0)}
        grid_res = E.evaluate_many(grid_pol, E.test_episodes(), workers=args.workers)
        grid = [E.episode_mean(r) for r in grid_res.values()]
        torch.save(dict(test=test, stress=stress, grid=grid), res_path)
    else:
        cache = torch.load(res_path, weights_only=False)
        test, stress, grid = cache["test"], cache["stress"], cache["grid"]

    agg_test, agg_stress = E.aggregate(test), E.aggregate(stress)
    E.save_rows_csv(test, os.path.join(tdir, "test_per_episode.csv"), E.test_episodes())
    E.save_rows_csv(stress, os.path.join(tdir, "stress_per_episode.csv"), E.stress_episodes())
    E.save_summary_csv(agg_test, os.path.join(tdir, "test_summary.csv"))
    E.save_summary_csv(agg_stress, os.path.join(tdir, "stress_summary.csv"))
    write_report(agg_test, agg_stress, test, stress, tuned, hists, order, seeds, algos)

    # 4 -- figures
    from . import plots as P
    recs = {}
    for c in baseline_names:
        recs[c] = MicrogridVSGEnv("combined").rollout(make_policy(c, tuned=tuned), seed=C.TEST_SEED)
    for a in algos:
        if hists[a]:
            s = representative_seed(hists[a])
            recs[a] = MicrogridVSGEnv("combined").rollout(agents[(a, s)].policy(), seed=C.TEST_SEED)
    log("\n[figures] ...")
    figs = [P.figure2_generation(), P.figure3_scenarios()]
    for a, num in (("ddpg", 4), ("td3", 5)):
        if a in recs:
            figs.append(P.figure_training(a, hists[a], recs, num))
    cmp_ctrl = ["none", "fixed_high", "fixed_tuned", "adaptive_rule"] + [a for a in algos if a in recs]
    figs.append(P.figure_comparison({a: hists[a] for a in algos if hists[a]}, recs, test, cmp_ctrl))
    figs.append(P.figure_metrics(agg_test, test, grid, stress, recs, order))

    log("\n" + "=" * 72)
    log(f"  COMPLETE in {time.time() - t0:.0f}s — outputs in {C.OUT_DIR}/")
    log(f"    report  {os.path.join(C.OUT_DIR, 'RESULTS.md')}")
    for f in figs:
        log(f"    figure  {f}")
    log("=" * 72)
    return 0


def write_report(agg_test, agg_stress, test, stress, tuned, hists, order, seeds, algos):
    from . import evaluate as E
    L = []
    L.append("# Results\n")
    L.append(f"Seeds: {seeds}. Episodes per run: {C.EPISODES}. "
             f"Weather: {C.WEATHER_SOURCE}. Test = five deterministic paper scenarios "
             f"(seed {C.TEST_SEED}); stress = {C.N_STRESS} randomised held-out episodes. "
             "RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). "
             "Baselines are deterministic and tuned on the validation episodes only.\n")
    ft, ar = tuned["fixed_tuned"], tuned["adaptive_rule"]
    L.append(f"* **Fixed tuned**: J = {ft['J']}, D = {ft['D']}, Kq = {ft['Kq']}  ")
    L.append(f"* **Rule-based adaptive**: J0 = {ar['J0']}, kJ = {ar['kJ']}, "
             f"D0 = {ar['D0']}, kD = {ar['kD']}, Kq = {ar['Kq']}\n")
    L.append("## Test scenarios (average of the five)\n")
    L.append(E.markdown_table(agg_test, order) + "\n")
    L.append("## Held-out stress test\n")
    L.append(E.markdown_table(agg_stress, order) + "\n")

    L.append("## Statistical comparisons (Welch t on per-seed means)\n")
    L.append("| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |")
    L.append("|---|---|---|---|---|---|")
    if "ddpg" in algos and "td3" in algos:
        for m in ("iae", "ise", "settle_s", "reserve_pu", "reward"):
            row = [f"TD3 − DDPG", m]
            for per, agg in ((test, agg_test), (stress, agg_stress)):
                ct = E.compare(per, "td3", "ddpg", m)
                d = agg["td3"][m][0] - agg["ddpg"][m][0]
                row += [f"{d:+.4f}", f"{ct[0]:+.2f}" if ct else "n/a"]
            L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("## RL vs best non-learning controller (seeds that beat it)\n")
    for a in algos:
        if a not in agg_test:
            continue
        for b in ("fixed_tuned", "adaptive_rule"):
            for m in ("iae", "reward"):
                for nm, per in (("test", test), ("stress", stress)):
                    base = E.episode_mean(per[(b, None)])[m]
                    vals = [E.episode_mean(r)[m] for (c, s), r in per.items() if c == a]
                    better = sum((v < base) if m != "reward" else (v > base) for v in vals)
                    L.append(f"* {a.upper()} vs {C.CONTROLLER_LABELS[b]} — {m} ({nm}): "
                             f"{better}/{len(vals)} seeds better "
                             f"(RL mean {np.mean(vals):.4g}, baseline {base:.4g})")
    L.append("")
    L.append("## Critic calibration at the selected checkpoint (validation states)\n")
    L.append("Bias = critic estimate − Monte-Carlo discounted return actually obtained.\n")
    L.append("| Algorithm | Seed | Q1 − G | min(Q1,Q2) − G |")
    L.append("|---|---|---|---|")
    for a in algos:
        for s, h in sorted(hists[a].items()):
            if not h.get("val_return"):
                continue
            i = int(np.argmax(h["val_return"]))
            L.append(f"| {a.upper()} | {s} | {h['q_bias'][i]:+.2f} | {h['q_min_bias'][i]:+.2f} |")
    with open(os.path.join(C.OUT_DIR, "RESULTS.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    log("\n".join(L))
