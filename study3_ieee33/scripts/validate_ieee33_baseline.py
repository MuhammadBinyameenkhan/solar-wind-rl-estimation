"""Validate the IEEE 33-bus data against the published base case before it is used.

1. MATPOWER and pandapower transcriptions of Baran & Wu (1989) must agree exactly.
2. The base-case load flow must reproduce the published results:
   real losses 202.7 kW, minimum voltage 0.9131 pu at bus 18 (slack 1.0 pu, 12.66 kV).
"""
import sys

import pandapower as pp
import pandapower.networks as pn

from ieee33_data import load_ieee33

buses, lines = load_ieee33()
net = pn.case33bw()
ln = net.line
diff = 0.0
for f, t, r, x in zip(ln.from_bus + 1, ln.to_bus + 1, ln.r_ohm_per_km * ln.length_km, ln.x_ohm_per_km * ln.length_km):
    m = lines[((lines["from"] == f) & (lines.to == t)) | ((lines["from"] == t) & (lines.to == f))]
    diff = max(diff, abs(m.r_ohm.iloc[0] - r), abs(m.x_ohm.iloc[0] - x))
pl = net.load.groupby("bus")[["p_mw", "q_mvar"]].sum()
dl = max(abs(buses.p_kw[b] / 1e3 - r.p_mw) + abs(buses.q_kvar[b] / 1e3 - r.q_mvar) for b, r in pl.iterrows())
pp.runpp(net, numba=False)
loss_kw = net.res_line.pl_mw.sum() * 1e3
vmin = net.res_bus.vm_pu.min(); vbus = int(net.res_bus.vm_pu.idxmin()) + 1
print(f"data agreement: max |dr|,|dx| = {diff:.1e} ohm, max |dload| = {dl:.1e} MW")
print(f"losses {loss_kw:.2f} kW (published 202.7); Vmin {vmin:.4f} pu at bus {vbus} (published 0.9131 at bus 18)")
ok = diff < 1e-9 and dl < 1e-9 and abs(loss_kw - 202.7) < 0.1 and abs(vmin - 0.9131) < 5e-4 and vbus == 18
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
