"""Shared episode runner used by training (validation), evaluation and plotting."""
from __future__ import annotations

from .metrics import episode_metrics


def run_episode(env, controller, scenario):
    """Run one deterministic episode; returns (metrics dict, trace DataFrame)."""
    obs, _ = env.reset(options={"scenario": scenario, "mode": getattr(controller, "mode", "vsg")})
    controller.reset()
    done = False
    info = {}
    while not done:
        obs, r, term, trunc, info = controller.step(env, obs)
        done = term or trunc
    ep = info["episode"]
    tr = env.trace_frame()
    m = episode_metrics(tr, scenario.to_dict(), env.cfg) if len(tr) else {}
    m.update({"return": ep["return"], "collapsed": ep["collapsed"]})
    return m, tr
