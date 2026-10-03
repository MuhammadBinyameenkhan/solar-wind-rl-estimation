function obs = vsgrl_build_obs(m, prev_a, p)
%VSGRL_BUILD_OBS  Normalised observation vector, identical to VSGEnv._obs().
%   m : struct of measurements (all in pu of S_base / f0 unless stated)
%       df, rocof        bus-frequency deviation and RoCoF (pu, pu/s), PLL-filtered
%       p_vsg            VSG incremental power
%       dfv_minus_df     VSG virtual-rotor minus diesel speed deviation (pu)
%       h_up, h_pv       upward headroom total / PV part
%       soc              BESS state of charge (0..1)
%       p_wind, pv_mpp, p_diesel, load0
%   prev_a : previous raw action (3x1)
f0 = p.system_f_nominal_hz;  Sb = p.system_s_base_mva;
Pd = p.system_diesel_rated_mw / Sb;
obs = [ m.df * f0 / p.system_grid_code_f_target_hz;
        m.rocof * f0 / p.system_grid_code_rocof_limit_hz_s;
        m.p_vsg / 0.25;
        m.dfv_minus_df * f0 / 0.1;
        m.h_up / 0.3;
        m.h_pv / 0.1;
        (m.soc - 0.5) / 0.4;
        m.p_wind * Sb / 1.0;
        m.pv_mpp * Sb / 0.8;
        m.p_diesel / Pd;
        (Pd - m.p_diesel) / Pd;
        m.load0 * Sb / 1.2;
        prev_a(:) ];
obs = min(max(obs, -10), 10);
end
