function [S, M] = vsgrl_episode(C, p, sc, ctrl, pol)
%VSGRL_EPISODE  Simulate one 30 s multi-event episode on the 50 ms decision grid.
%   ctrl.type = 'fixed'    constant (ctrl.H, ctrl.D, ctrl.alpha), no projection
%               'feasible' the same constants clipped to the headroom projection
%               'policy'   exported RL actor (pol) with its residual mapping and projection
%   Mirrors VSGEnv.reset / step / step_params and the baseline controllers in vsgrl/.
S = vsgrl_reset(C, sc);
applied = [];  ret = 0;  collapsed = false;
for kstep = 1:C.max_steps
    bounds = local_bounds(C, S, p);
    switch ctrl.type
        case 'fixed'
            par = [ctrl.H; ctrl.D; ctrl.alpha];  enforce = false;
        case 'feasible'
            par = [min(ctrl.H, bounds(1)); min(ctrl.D, bounds(2)); ctrl.alpha];  enforce = p.env_headroom_constraint > 0;
        case 'policy'
            if isempty(applied)
                app = [p.system_vsg_nominal_h_s; p.system_vsg_nominal_d_pu; p.system_vsg_nominal_alpha];
            else
                app = applied;
            end
            m = struct('df', S.f_meas, 'rocof', S.rocof_meas, 'p_vsg', S.p_vsg, 'dfv_minus_df', S.dw_v - S.dw_d, ...
                       'h_up', vsgrl_headroom(C, S, 'up'), 'h_dn', vsgrl_headroom(C, S, 'down'), 'h_pv', S.h_pv, ...
                       'soc', S.soc, 'p_wind', S.p_w, 'pv_mpp', S.pv_mpp, 'p_diesel', S.p_d, 'load0', S.load0);
            obs = vsgrl_build_obs(m, app, p);
            [H, D, al] = vsgrl_policy(obs, pol, bounds);
            par = [H; D; al];  enforce = pol.headroom_constraint > 0;
    end
    if ~strcmp(ctrl.type, 'policy')               % baselines clip to the static ranges
        par(1) = min(max(par(1), C.h_min), C.h_max);
        par(2) = min(max(par(2), C.d_min), C.d_max);
    end
    if C.param_tau > 0 && ~isempty(applied)       % rate limit (tau = 0.25 s) ...
        kf = min(C.agent_dt / C.param_tau, 1);
        par = applied + kf * (par - applied);
    end
    if enforce                                     % ... then feasibility before smoothness
        par(1) = min(par(1), bounds(1));  par(2) = min(par(2), bounds(2));
    end
    applied = par;
    [S, st] = vsgrl_advance(C, S, par(1), par(2), par(3), C.n_sub, true);
    cost = C.w.freq * st.msf_excess_hz2 / C.f_target^2 + C.w.inband * st.msf_hz2 / C.f_target^2 ...
         + C.w.rocof * st.msr_excess_hz2s2 / C.rocof_limit_hz^2 + C.w.bess * st.ms_pbess / C.Pb_max^2 ...
         + C.w.fast * st.ms_pfast / C.Pb_max^2 + C.w.sat * st.mean_sat / 0.05 + C.w.viol * st.viol_frac;
    ret = ret - cost;
    if abs(S.f_meas) * C.f0 > C.term_hz || ~isfinite(S.f_meas)
        ret = ret - C.w.collapse;  collapsed = true;  break
    end
end
S.trace = S.trace(1:S.n_tr, :);
M = vsgrl_metrics(C, S, sc);
M.return = ret;  M.collapsed = collapsed;
end

function b = local_bounds(C, S, p)
% band-power feasibility projection via the deployable helper (same function Simulink would use)
b = vsgrl_headroom_bounds(vsgrl_headroom(C, S, 'auto'), S.load0, p);
end
