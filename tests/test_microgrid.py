import numpy as np
import pytest

from vsgrl.data.hybrid import wind_curve_from_cfg
from vsgrl.microgrid import Microgrid, Scenario


@pytest.fixture
def mg(cfg):
    c = dict(cfg)
    c["system"] = {**cfg["system"], "wind": {**cfg["system"]["wind"], "turbulence_intensity": 0.0},
                   "load": {**cfg["system"]["load"], "noise_frac": 0.0}}
    return Microgrid(c, wind_curve_from_cfg(c))


def sc(dist=0.3, soc=0.6, ws=9.0, pv=0.5, load=1.0):
    return Scenario("t", ws, 1.2, pv, load, soc, dist, 1.0, 1)


@pytest.mark.parametrize("mode", ["vsg", "droop", "none"])
def test_equilibrium_without_disturbance(mg, mode):
    mg.reset(sc(dist=0.0), 5.0)
    mg.advance(3.0, 20.0, 0.3, 2500, mode=mode)
    assert abs(mg.f_meas) < 1e-9 and abs(mg.p_vsg) < 1e-9


def test_vsg_beats_droop_on_rocof_and_supports(mg):
    out = {}
    for mode in ("droop", "vsg"):
        mg.reset(sc(), 10.0)
        tr = {"every": 5, "rows": []}
        mg.advance(3.0, 20.0, 0.3, 5000, mode=mode, trace=tr)
        r = np.array(tr["rows"])
        out[mode] = (np.abs(r[:, 1]).max(), np.abs(r[:, 2]).max(), mg.soc)
    assert out["vsg"][1] < out["droop"][1]            # lower RoCoF with inertia
    assert out["vsg"][2] < 0.6                         # BESS discharged for an under-frequency event


@pytest.mark.parametrize("H,D", [(0.2, 0.0), (0.2, 50.0), (8.0, 0.0), (8.0, 50.0)])
def test_stable_at_parameter_extremes(mg, H, D):
    """Numerical stability of the symplectic integrator over the whole action range
    (step small enough that the diesel can cover it even with D_v = 0)."""
    mg.reset(sc(dist=0.1), 10.0)
    mg.advance(H, D, 1.0, 5000, mode="vsg")
    assert np.isfinite(mg.f_meas) and abs(mg.f_meas * 50) < 3.0


def test_headroom_saturation(mg):
    mg.reset(sc(dist=0.4, soc=0.12, pv=0.0, load=0.7), 10.0)
    st = mg.advance(8.0, 50.0, 0.0, 5000, mode="vsg")
    assert st["mean_sat"] > 0                          # requested power exceeded what the BESS can give
    dis, _ = mg.bess_limits(mg.soc)
    assert mg.pb0 + mg.p_vsg - mg.p_pv_s <= dis + 1e-9
