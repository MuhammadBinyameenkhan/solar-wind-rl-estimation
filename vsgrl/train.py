"""Training loop for TD3 / DDPG on the VSG environment (one seed)."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

from .agents.td3 import TD3Agent
from .config import resolve_path
from .data.hybrid import load_processed
from .envs import VSGEnv, make_env

log = logging.getLogger(__name__)


def evaluate_policy(env: VSGEnv, agent: TD3Agent, scenarios) -> dict:
    rets, devs, rocofs, col = [], [], [], []
    for sc in scenarios:
        obs, _ = env.reset(options={"scenario": sc})
        done = False
        while not done:
            obs, r, term, trunc, info = env.step(agent.act(obs, noise=0.0))
            done = term or trunc
        ep = info["episode"]
        rets.append(ep["return"]); devs.append(ep["max_df_hz"])
        rocofs.append(ep["max_rocof_hz_s"]); col.append(ep["collapsed"])
    return {"val_return": float(np.mean(rets)), "val_max_df_hz": float(np.mean(devs)),
            "val_max_rocof": float(np.mean(rocofs)), "val_collapse_rate": float(np.mean(col))}


def train_one(cfg: dict, algo: str, seed: int, out_dir: Path, df: pd.DataFrame | None = None) -> Path:
    """Train one seed. The full training state is written to <out_dir>/resume.pt at every validation;
    if that file exists the run continues from it (same result as an uninterrupted run), and a run
    that already finished (summary.json) is skipped."""
    torch.set_num_threads(1)
    t = cfg["train"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "summary.json").exists():
        log.info("[%s seed %d] already finished: %s", algo, seed, out_dir)
        return out_dir
    resume = out_dir / "resume.pt"
    if resume.exists():
        old = yaml.safe_load((out_dir / "config.yaml").read_text())
        if old != yaml.safe_load(yaml.safe_dump(cfg, sort_keys=False)):
            raise RuntimeError(f"{out_dir}: config differs from the interrupted run; delete the folder to restart")
    with open(out_dir / "config.yaml", "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)

    df = df if df is not None else load_processed(cfg)
    env = make_env(cfg, df, split="train")
    val_env = make_env(cfg, df, split="val")
    val_set = val_env.sampler.fixed_set("val", t["eval_episodes"], cfg["eval"]["scenario_seed"] + 1)
    agent = TD3Agent(env.observation_space.shape[0], env.action_space.shape[0], t, algo=algo, seed=seed)

    rng = np.random.default_rng(seed)
    n_ep = t["episodes"]
    if resume.exists():
        st = torch.load(resume, map_location="cpu", weights_only=False)
        agent.load_state(st["agent"])
        rng.bit_generator.state = st["rng"]
        env._rng.bit_generator.state = st["env_rng"]
        env.sampler.stats = st["sampler_stats"]
        best, vrows, rows = st["best"], st["vrows"], st["rows"]
        total_steps, upd_credit, ep0, t_used = st["total_steps"], st["upd_credit"], st["episode"], st["wall_s"]
        log.info("[%s seed %d] resumed after episode %d", algo, seed, ep0)
    else:
        # Episode-0 validation: the untrained (zero-initialised residual) policy = base controller,
        # so model selection never returns a policy worse than where training started.
        v0 = evaluate_policy(val_env, agent, val_set)
        best = v0["val_return"]
        agent.save(out_dir / "best.pt")
        vrows = [dict(v0, episode=0, steps=0)]
        log.info("[%s seed %d] ep 0 (untrained)  val R=%.2f", algo, seed, best)
        total_steps, upd_credit, ep0, t_used = 0, 0.0, 0, 0.0
        rows = []
    t0 = time.time() - t_used
    for ep in range(ep0 + 1, n_ep + 1):
        obs, _ = env.reset(seed=seed) if ep == 1 else env.reset()
        noise = t["expl_noise"] + (t["expl_noise_final"] - t["expl_noise"]) * (ep - 1) / max(n_ep - 1, 1)
        done, Hs, Ds, As, closs = False, [], [], [], []
        while not done:
            if total_steps < t["warmup_steps"]:
                a = rng.uniform(-1, 1, env.action_space.shape).astype(np.float32)
            else:
                a = agent.act(obs, noise=noise)
            obs2, r, term, trunc, info = env.step(a)
            agent.buffer.add(obs, a, r, obs2, float(term))   # truncation bootstraps
            obs, done = obs2, term or trunc
            total_steps += 1
            Hs.append(info["H"]); Ds.append(info["D"]); As.append(info["alpha"])
            if total_steps >= t["warmup_steps"]:
                upd_credit += t["updates_per_step"]          # may be fractional (0.5 = every 2nd step)
                while upd_credit >= 1.0:
                    closs.append(agent.update()["critic_loss"])
                    upd_credit -= 1.0
        e = info["episode"]
        sc = env.scenario
        rows.append({"episode": ep, "steps": total_steps, "return": e["return"], "max_df_hz": e["max_df_hz"],
                     "max_rocof_hz_s": e["max_rocof_hz_s"], "sat_s": e["sat_s"], "collapsed": e["collapsed"],
                     "mean_H": np.mean(Hs), "mean_D": np.mean(Ds), "mean_alpha": np.mean(As),
                     "dist_mw": sc.dist_mw, "critic_loss": np.mean(closs) if closs else np.nan,
                     "noise": noise, "wall_s": time.time() - t0})
        if ep % t["eval_every"] == 0 or ep == n_ep:
            v = evaluate_policy(val_env, agent, val_set)
            v.update({"episode": ep, "steps": total_steps})
            vrows.append(v)
            if v["val_return"] > best:
                best = v["val_return"]
                agent.save(out_dir / "best.pt")
            log.info("[%s seed %d] ep %d/%d  train R=%.2f  val R=%.2f  val |Δf|max=%.3f Hz  (%.0fs)",
                     algo, seed, ep, n_ep, e["return"], v["val_return"], v["val_max_df_hz"], time.time() - t0)
            pd.DataFrame(rows).to_csv(out_dir / "train_log.csv", index=False)
            pd.DataFrame(vrows).to_csv(out_dir / "val_log.csv", index=False)
            tmp = out_dir / "resume.pt.tmp"
            torch.save({"agent": agent.state(), "rng": rng.bit_generator.state,
                        "env_rng": env._rng.bit_generator.state, "sampler_stats": env.sampler.stats,
                        "best": best, "vrows": vrows, "rows": rows, "total_steps": total_steps,
                        "upd_credit": upd_credit, "episode": ep, "wall_s": time.time() - t0}, tmp)
            tmp.replace(resume)
    agent.save(out_dir / "final.pt")
    with open(out_dir / "summary.json", "w") as fh:
        json.dump({"algo": algo, "seed": seed, "episodes": n_ep, "steps": total_steps,
                   "best_val_return": best, "wall_s": time.time() - t0,
                   "train_scenario_rejection_rate": env.sampler.rejection_rate("train")}, fh, indent=2)
    resume.unlink(missing_ok=True)
    return out_dir


def run_dir(cfg, algo, seed, tag=None) -> Path:
    return resolve_path(cfg["train"]["out_dir"]) / (tag or algo) / f"seed{seed}"
