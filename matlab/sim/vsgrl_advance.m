function [S, st] = vsgrl_advance(C, S, H_v, D_v, alpha, n_steps, record)
%VSGRL_ADVANCE  Integrate n_steps x 2 ms of the two-machine RMS model with a grid-forming VSG.
%   Symplectic Euler; mirrors Microgrid.advance (mode "vsg") in vsgrl/microgrid.py.
%   st: interval statistics used by the reward.
dt = C.dt;  w0 = C.w0;  Sb = C.Sb;  Kd = C.Kd;  Ks = C.Ks;  Ksum = Kd + Ks;
H2d = 2 * C.H_d;  H2v = 2 * max(H_v, 1e-3);  DLP = C.DL * S.load0;
sum_f2 = 0; sum_r2 = 0; sum_pb2 = 0; sum_sat = 0; sum_ef2 = 0; sum_er2 = 0; sum_fast2 = 0; n_viol = 0;
for step = 1:n_steps
    k = S.k;  t = S.t;
    % --- exogenous inputs
    v = S.sc.ws_hub_ms * (1 + C.TI * S.sc.turb(k + 1));
    pw_t = min(vsgrl_wind_power(C, max(v, 0), S.sc.rho_kgm3) / Sb, S.wind_cap);
    load = S.load0 * (1 + C.load_noise * S.sc.lnoise(k + 1));
    while S.ev_i <= numel(S.ev_t) && t >= S.ev_t(S.ev_i)
        S.load_step = S.load_step + S.ev_p(S.ev_i);  S.ev_i = S.ev_i + 1;
    end
    load = load + S.load_step;
    % --- network solution and headroom-limited VSG power
    dP = (load - S.load0) - (S.p_w - S.p_w0) + DLP * S.f_meas;
    [dis, ch] = vsgrl_bess_limits(C, S.soc);
    hi = dis - S.pb0 + S.p_pv_s;
    lo = -(ch + S.pb0) + S.p_pv_s;
    pv_req = Ks * (Kd * S.delta + dP) / Ksum;
    pv = min(max(pv_req, lo), hi);
    sat = abs(pv_req - pv);
    pd_e = dP - pv;
    % --- rotor velocities first (symplectic Euler)
    acc_d = (S.p_d - S.pd0 - pd_e - C.D_d * (S.dw_d - S.dw_b)) / H2d;
    S.dw_d = S.dw_d + dt * acc_d;
    S.dw_v = S.dw_v + dt * (S.p_set - pv - D_v * S.dw_v) / H2v;
    S.delta = S.delta + dt * w0 * (S.dw_v - S.dw_d);
    if sat > 0                                   % current limit: angle anti-windup
        S.delta = (pv * Ksum / Ks - dP) / Kd;
        S.dw_v = S.dw_d;  S.dw_b = S.dw_d;
    else
        S.dw_b = (Kd * S.dw_d + Ks * S.dw_v) / Ksum;
    end
    pv_tgt = min(max(alpha * pv_req, -S.pv_base), S.h_pv);
    S.p_pv_s = S.p_pv_s + dt * (pv_tgt - S.p_pv_s) / C.Tpv;
    S.p_vsg = pv;
    % --- diesel governor (droop) + AGC, BESS secondary control
    p_ref = S.pd0 - C.inv_R * S.f_meas + S.x_agc;
    S.x_agc = S.x_agc - dt * C.Ki * S.f_meas;
    if C.Ki_b > 0
        S.p_set = min(max(S.p_set - dt * C.Ki_b * S.f_meas, lo), hi);
    end
    S.p_gov = S.p_gov + dt * (p_ref - S.p_gov) / C.Tg;
    S.p_gov = min(max(S.p_gov, 0), C.Pd_rat);
    dpd = min(max((S.p_gov - S.p_d) / C.Te, -C.ramp), C.ramp);
    S.p_d = min(max(S.p_d + dt * dpd, 0), C.Pd_rat);
    % --- wind electrical power
    S.p_w = S.p_w + dt * (pw_t - S.p_w) / C.Trot;
    % --- BESS energy
    p_b = S.pb0 + pv - S.p_pv_s;  p_b_mw = p_b * Sb;
    if p_b_mw >= 0
        S.soc = S.soc - p_b_mw / C.eta_d / C.Eb * dt / 3600;
    else
        S.soc = S.soc - p_b_mw * C.eta_c / C.Eb * dt / 3600;
    end
    % --- bus-frequency measurement (PLL low-pass) and RoCoF
    S.rocof_meas = (S.dw_b - S.f_meas) / C.Tf;
    S.f_meas = S.f_meas + dt * S.rocof_meas;
    % --- statistics
    fm = S.f_meas;  rm = S.rocof_meas;
    sum_f2 = sum_f2 + fm^2;  sum_r2 = sum_r2 + rm^2;
    ef = abs(fm) - C.f_band;  if ef > 0, sum_ef2 = sum_ef2 + ef^2; end
    er = abs(rm) - C.r_band;  if er > 0, sum_er2 = sum_er2 + er^2; end
    sum_pb2 = sum_pb2 + (p_b - S.pb0)^2;
    sum_fast2 = sum_fast2 + (pv - S.p_set)^2;
    sum_sat = sum_sat + sat;
    if abs(fm) > C.f_lim || abs(rm) > C.r_lim, n_viol = n_viol + 1; end
    S.k = k + 1;  S.t = t + dt;
    if record && mod(k, C.trace_every) == 0
        S.n_tr = S.n_tr + 1;
        S.trace(S.n_tr, :) = [S.t, fm*C.f0, rm*C.f0, pv*Sb, p_b_mw, S.p_d*Sb, S.soc, H_v, D_v, alpha, ...
                              S.p_set*Sb, vsgrl_headroom(C, S, 'auto')*Sb, sat*Sb];
    end
end
n = n_steps;  f02 = C.f0^2;
st = struct('msf_hz2', sum_f2/n*f02, 'msr_hz2s2', sum_r2/n*f02, 'msf_excess_hz2', sum_ef2/n*f02, ...
            'msr_excess_hz2s2', sum_er2/n*f02, 'ms_pbess', sum_pb2/n, 'ms_pfast', sum_fast2/n, ...
            'mean_sat', sum_sat/n, 'viol_frac', n_viol/n);
end
