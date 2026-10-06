"""
Metrics, test sweeps, held-out stress test and multi-seed statistics.

Metric definitions (all computed identically for every controller):

  nadir_hz        lowest frequency during contingency 1 (load increase)
  zenith_hz       highest frequency during contingency 2 (load decrease)
  df_max_hz       largest |f - f0| over the episode
  overshoot_pct   rebound above f0 after the contingency-1 nadir and BEFORE
                  contingency 2 starts, as % of the nadir depth.  [Fix: the
                  old metric took the max after the nadir over the whole
                  episode, i.e. it measured contingency 2.]
  rocof_win       peak 500 ms-window RoCoF (relay view)
  settle_s        time after the last contingency clears until |df| < 0.05 Hz
                  permanently;  settle1_s the same after contingency 1
                  (measured up to the start of contingency 2)
  iae / ise / itae
  reserve_pu      mean DELIVERED headroom commitment (Eq. 22 with J_eff, D_eff)
  reserve_req_pu  mean DECLARED headroom requirement (Eq. 22 with J, D)
  derate_pct      % of steps with h_req > h_avail
  E_vsg_kwh       battery energy spent on the VSG term
"""
import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import config as C
from .env import MicrogridVSGEnv
from .utils import mean_ci95, trapz, welch_t

SETTLE_BAND = 0.05


def _settle(t, err, t_from, t_to, band=SETTLE_BAND):
    idx = np.where((t >= t_from) & (t < t_to))[0]
    if len(idx) == 0:
        return float("nan")
    inside = np.abs(err[idx]) < band
    # last sample outside the band
    out = np.where(~inside)[0]
    if len(out) == 0:
        return 0.0
    if out[-1] == len(idx) - 1:
        return float(t_to - t_from)
    return float(t[idx[out[-1] + 1]] - t_from)


def compute_metrics(rec: dict) -> dict:
    t, f = rec["t"], rec["f"]
    err = f - C.F_NOM
    (a1, b1), (a2, b2) = rec["event_windows"][0], rec["event_windows"][-1]

    w1 = (t >= a1) & (t < a2)
    i_nad = np.where(w1)[0][np.argmin(f[w1])]
    nadir = float(f[i_nad])
    reb = (t >= t[i_nad]) & (t < a2)
    over_hz = float(max(0.0, f[reb].max() - C.F_NOM))
    depth = C.F_NOM - nadir
    w2 = t >= a2
    zenith = float(f[w2].max())

    res = lambda J, D: 2.0 * J * (C.ROCOF_LIMIT / C.F_NOM) + D * (C.F_BAND_OK / C.F_NOM)
    return {
        "nadir_hz": nadir,
        "zenith_hz": zenith,
        "df_max_hz": float(np.abs(err).max()),
        "overshoot_hz": over_hz,
        "overshoot_pct": float(100.0 * over_hz / depth) if depth > 1e-6 else 0.0,
        "rocof_win": float(np.abs(rec["rocof"]).max()),
        "rocof_raw": float(np.abs(rec["rocof_inst"]).max()),
        "settle1_s": _settle(t, err, b1, a2),
        "settle_s": _settle(t, err, b2, t[-1] + 1e-9),
        "t_outside_band_s": float(np.sum(np.abs(err) > C.F_BAND_OK) * (t[1] - t[0])),
        "iae": float(trapz(np.abs(err), t)),
        "ise": float(trapz(err ** 2, t)),
        "itae": float(trapz(t * np.abs(err), t)),
        "v_min": float(rec["V"].min()),
        "dv_max": float(np.abs(rec["V"] - C.V_NOM).max()),
        "E_vsg_kwh": float(trapz(np.abs(rec["P_vsg"]), t) / 3.6e6),
        "reserve_pu": float(np.mean(res(rec["J_eff"], rec["D_eff"]))),
        "reserve_req_pu": float(np.mean(res(rec["J"], rec["D"]))),
        "derate_pct": float(100.0 * np.mean(rec["h_req"] > rec["h_avail"] + 1e-9)),
        "J_mean": float(rec["J"].mean()),
        "D_mean": float(rec["D"].mean()),
        "reward": float(rec["total_reward"]),
        "tripped": float(rec["tripped"]),
    }


METRIC_KEYS = ["nadir_hz", "zenith_hz", "df_max_hz", "overshoot_pct", "rocof_win",
               "settle1_s", "settle_s", "iae", "ise", "itae", "v_min", "dv_max",
               "E_vsg_kwh", "reserve_pu", "reserve_req_pu", "derate_pct",
               "J_mean", "D_mean", "reward", "tripped"]


def test_episodes():
    return [(sc, False, C.TEST_SEED) for sc in C.EVAL_SCENARIOS]


def stress_episodes(n=None):
    n = C.N_STRESS if n is None else n
    return [(C.EVAL_SCENARIOS[i % len(C.EVAL_SCENARIOS)], True, C.STRESS_SEED0 + i)
            for i in range(n)]


def run_episode(policy, scenario, stochastic, seed):
    env = MicrogridVSGEnv(scenario=scenario, stochastic=stochastic)
    return env.rollout(policy, seed=seed)


def _eval_job(job):
    key, policy, episodes, overrides = job
    for k, v in overrides.items():
        setattr(C, k, v)
    import torch
    torch.set_num_threads(1)
    return key, [compute_metrics(run_episode(policy, *e)) for e in episodes]


def evaluate_many(policies: dict, episodes, workers: int = 4) -> dict:
    """{key: policy} -> {key: [metrics per episode]} (parallel over keys)."""
    from .train import config_overrides
    jobs = [(k, p, episodes, config_overrides()) for k, p in policies.items()]
    if workers <= 1:
        return dict(_eval_job(j) for j in jobs)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(_eval_job, jobs))


def episode_mean(rows: list) -> dict:
    return {k: float(np.mean([r[k] for r in rows])) for k in METRIC_KEYS}


# ----------------------------------------------------------------
# Aggregation:  keys are (controller, seed); seed None for baselines
# ----------------------------------------------------------------
def aggregate(per_key: dict) -> dict:
    """controller -> metric -> (mean over seeds, sd, ci95, n_seeds)
    where each seed's value is the mean over the episodes."""
    by_c = {}
    for (c, seed), rows in per_key.items():
        by_c.setdefault(c, []).append(episode_mean(rows))
    out = {}
    for c, seed_means in by_c.items():
        out[c] = {k: (*mean_ci95([m[k] for m in seed_means]), len(seed_means))
                  for k in METRIC_KEYS}
    return out


def compare(per_key: dict, a: str, b: str, metric: str):
    """Welch t on the per-seed means of controller a vs b."""
    va = [episode_mean(r)[metric] for (c, s), r in per_key.items() if c == a]
    vb = [episode_mean(r)[metric] for (c, s), r in per_key.items() if c == b]
    if len(va) < 2 or len(vb) < 2:
        return None
    return welch_t(va, vb)


# ----------------------------------------------------------------
# Output
# ----------------------------------------------------------------
TABLE_COLS = [("iae", "IAE (Hz·s)", "{:.3f}"), ("ise", "ISE (Hz²·s)", "{:.3f}"),
              ("itae", "ITAE (Hz·s²)", "{:.2f}"), ("nadir_hz", "Nadir (Hz)", "{:.3f}"),
              ("rocof_win", "RoCoF (Hz/s)", "{:.3f}"), ("settle_s", "Settling (s)", "{:.3f}"),
              ("overshoot_pct", "Overshoot (%)", "{:.1f}"),
              ("reserve_pu", "Reserve (pu)", "{:.3f}"), ("derate_pct", "Derated (%)", "{:.1f}"),
              ("E_vsg_kwh", "E_vsg (kWh)", "{:.3f}"), ("tripped", "Trip rate", "{:.2f}")]


def save_rows_csv(per_key: dict, path: str, episodes):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["controller", "seed", "scenario", "stochastic", "episode_seed"] + METRIC_KEYS)
        for (c, seed), rows in per_key.items():
            for (sc, st, es), r in zip(episodes, rows):
                w.writerow([c, "" if seed is None else seed, sc, int(st), es]
                           + [f"{r[k]:.6g}" for k in METRIC_KEYS])


def save_summary_csv(agg: dict, path: str):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        hdr = ["controller", "n_seeds"]
        for k in METRIC_KEYS:
            hdr += [f"{k}_mean", f"{k}_sd", f"{k}_ci95"]
        w.writerow(hdr)
        for c, m in agg.items():
            row = [c, m[METRIC_KEYS[0]][3]]
            for k in METRIC_KEYS:
                row += [f"{m[k][0]:.6g}", f"{m[k][1]:.6g}", f"{m[k][2]:.6g}"]
            w.writerow(row)


def markdown_table(agg: dict, order) -> str:
    lines = ["| Controller | " + " | ".join(h for _, h, _ in TABLE_COLS) + " |",
             "|---|" + "---|" * len(TABLE_COLS)]
    for c in order:
        if c not in agg:
            continue
        cells = []
        for k, _, fmt in TABLE_COLS:
            mu, sd, ci, n = agg[c][k]
            cells.append(fmt.format(mu) + (f" ± {fmt.format(ci)}" if n > 1 else ""))
        n = agg[c][TABLE_COLS[0][0]][3]
        lab = C.CONTROLLER_LABELS.get(c, c) + (f" (n={n})" if n > 1 else "")
        lines.append(f"| {lab} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def save_json(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)


def tables_dir():
    d = os.path.join(C.OUT_DIR, "tables")
    os.makedirs(d, exist_ok=True)
    return d
