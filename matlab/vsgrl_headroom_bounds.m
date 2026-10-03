function bounds = vsgrl_headroom_bounds(h_up_pu, load0_pu, p)
%VSGRL_HEADROOM_BOUNDS  Feasibility projection of (H, D) onto available headroom.
%   Mirrors VSGEnv.param_bounds() in vsgrl/envs/vsg_env.py exactly.
%   h_up_pu  : direction-aware headroom [pu S_base]:
%              if df <= 0 (under-frequency / pre-event): BESS discharge limit(SoC) - P_bess0 + d*P_pv,mpp
%              if df >  0 (over-frequency):              BESS charge limit(SoC) + P_bess0 + P_pv,base
%   load0_pu : pre-event load [pu S_base]
%   p        : struct from vsgrl_params.mat
Sb   = p.system_s_base_mva;
dP   = p.system_disturbance_design_step_mw / Sb;
Pd   = p.system_diesel_rated_mw / Sb;
invR = Pd / p.system_diesel_droop;
beta = invR + p.system_load_damping_pu * load0_pu;
Ks = p.system_vsg_sync_coeff_pu;  Kd = p.system_diesel_sync_coeff_pu;
share0 = Ks / (Ks + Kd);
if ~p.env_headroom_constraint
    bounds = [p.system_vsg_h_max_s, p.system_vsg_d_max_pu];
    return
end
s = min(h_up_pu / dP, 0.95);
d_ub = min(p.system_vsg_d_max_pu, max(p.system_vsg_d_min_pu, beta * s / (1 - s)));
rho = min(1, h_up_pu / (share0 * dP));
h_ub = p.system_vsg_h_min_s + rho * (p.system_vsg_h_max_s - p.system_vsg_h_min_s);
bounds = [h_ub, d_ub];
end
