"""Scenario sampling from the real-data hourly operating points."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .microgrid import Microgrid, Scenario


class ScenarioSampler:
    def __init__(self, cfg: dict, df: pd.DataFrame, microgrid: Microgrid):
        self.cfg = cfg
        self.mg = microgrid
        self.splits = {k: g for k, g in df.groupby("split")}
        self.stats = {}

    def _draw(self, rng, row, ts) -> Scenario:
        s = self.cfg["system"]
        dist = s["disturbance"]
        mag = rng.uniform(*dist["step_mw_range"])
        sign = 1.0 if rng.random() < dist["prob_load_increase"] else -1.0
        return Scenario(
            time_utc=str(ts), ws_hub_ms=float(row.ws_hub_ms), rho_kgm3=float(row.rho_kgm3),
            p_pv_mpp_mw=float(row.p_pv_mpp_mw), load_mw=float(row.load_mw),
            soc0=float(rng.uniform(*s["bess"]["soc_init_range"])),
            dist_mw=sign * mag, dist_time_s=float(rng.uniform(*dist["time_s_range"])),
            noise_seed=int(rng.integers(0, 2**31 - 1)), split=row.split,
        )

    def is_adequate(self, sc: Scenario) -> bool:
        """N-1-style screen: upward reserve must cover a load increase; no load shed at dispatch."""
        mg = self.mg
        mg.reset(sc, 0.01)
        if mg.load_clipped > 1e-9:
            return False
        if sc.dist_mw <= 0:
            return True
        reserve = (mg.Pd_rat - mg.pd0) + mg.headroom_up()
        margin = self.cfg["system"]["disturbance"].get("adequacy_margin", 1.0)
        return reserve * mg.Sb >= margin * sc.dist_mw

    def sample(self, rng: np.random.Generator, split="train", max_tries=200) -> Scenario:
        g = self.splits[split]
        st = self.stats.setdefault(split, {"drawn": 0, "rejected": 0})
        for _ in range(max_tries):
            i = int(rng.integers(len(g)))
            sc = self._draw(rng, g.iloc[i], g.index[i])
            st["drawn"] += 1
            if self.is_adequate(sc):
                return sc
            st["rejected"] += 1
        raise RuntimeError(f"No adequate operating point found in split '{split}' after {max_tries} tries.")

    def fixed_set(self, split: str, n: int, seed: int) -> list[Scenario]:
        """Deterministic evaluation set (identical for every controller and seed)."""
        rng = np.random.default_rng(seed)
        return [self.sample(rng, split) for _ in range(n)]

    def rejection_rate(self, split):
        st = self.stats.get(split, {"drawn": 0, "rejected": 0})
        return st["rejected"] / max(st["drawn"], 1)


def scenarios_to_frame(scs: list[Scenario]) -> pd.DataFrame:
    return pd.DataFrame([s.to_dict() for s in scs])


def scenarios_from_frame(df: pd.DataFrame) -> list[Scenario]:
    return [Scenario(**{k: r[k] for k in Scenario.__dataclass_fields__}) for _, r in df.iterrows()]
