"""VSG environment of Study 2 running on the islanded IEEE 33-bus feeder."""
import numpy as np

from vsgrl.data.hybrid import wind_curve_from_cfg
from vsgrl.envs import VSGEnv

from .microgrid33 import Ieee33Microgrid

STUDY2_SB = 2.0     # MVA; MW-based observations are rescaled to the Study 2 plant size


class Ieee33VSGEnv(VSGEnv):
    def __init__(self, cfg, df, **kw):
        super().__init__(cfg, df, **kw)
        self.mg = Ieee33Microgrid(cfg, wind_curve_from_cfg(cfg))
        self.sampler.mg = self.mg

    def _obs(self):
        o = super()._obs()
        k = self.mg.Sb / STUDY2_SB          # plant scale factor (4.644 for the published feeder)
        for i in (8, 9, 12):                # wind power, PV MPP and load (MW-based in Study 2)
            o[i] = np.float32(o[i] / k)
        return o
