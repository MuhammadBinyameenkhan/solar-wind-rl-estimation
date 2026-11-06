"""IEEE 33-bus distribution feeder (Baran & Wu, 1989) — published data, verified.

Source data: MATPOWER case33bw.m (copied unchanged to data/source/case33bw_matpower.m), which
transcribes M. E. Baran and F. F. Wu, "Network reconfiguration in distribution systems for loss
reduction and load balancing," IEEE Trans. Power Del., vol. 4, no. 2, pp. 1401-1407, 1989,
doi:10.1109/61.25627. Cross-checked against pandapower.networks.case33bw (identical r, x, loads).

Nothing in this file is tuned or assumed: line r/x in ohm, loads in kW/kVAr, 12.66 kV base,
32 in-service lines and 5 normally open tie lines, exactly as published.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "data" / "source" / "case33bw_matpower.m"
V_BASE_KV = 12.66


def _block(text, name):
    b = text[text.index(f"mpc.{name} = ["):]
    b = b[b.index("\n") + 1:b.index("];")]
    rows = [l.split(";")[0].split() for l in b.strip().splitlines()
            if l.strip() and not l.strip().startswith("%")]
    return np.array([[float(x) for x in r] for r in rows])


def load_ieee33():
    """Return (buses, lines): buses[bus, p_kw, q_kvar], lines[from, to, r_ohm, x_ohm, in_service]."""
    t = SRC.read_text()
    bus, br = _block(t, "bus"), _block(t, "branch")
    buses = pd.DataFrame({"bus": bus[:, 0].astype(int), "p_kw": bus[:, 2], "q_kvar": bus[:, 3]})
    lines = pd.DataFrame({"from": br[:, 0].astype(int), "to": br[:, 1].astype(int),
                          "r_ohm": br[:, 2], "x_ohm": br[:, 3], "in_service": br[:, 10] == 1})
    return buses, lines


if __name__ == "__main__":
    b, l = load_ieee33()
    b.to_csv(SRC.parents[1] / "ieee33_buses.csv", index=False)
    l.to_csv(SRC.parents[1] / "ieee33_lines.csv", index=False)
    print(f"{len(b)} buses, {int(l.in_service.sum())} lines in service, {int((~l.in_service).sum())} tie lines; "
          f"load {b.p_kw.sum():.0f} kW / {b.q_kvar.sum():.0f} kVAr")
