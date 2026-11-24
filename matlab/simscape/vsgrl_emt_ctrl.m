function [vv, vd, il, mon] = vsgrl_emt_ctrl(meas, P)
%VSGRL_EMT_CTRL  Controls and slow plant dynamics of the circuit-level (EMT) microgrid model.
%   Called every P.Ts (100 us) by the MATLAB Function block of vsgrl_emt.slx (and by the
%   Simulink-free test bench vsgrl_emt_bench.m). All states are persistent; they are
%   re-initialised at the start of every simulation.
%
%   meas (12x1, previous step, SI units):
%     [v_bus_abc (V); i_vsg_abc (A, VSG -> bus); i_dsl_abc (A, diesel -> bus); i_load_abc (A, bus -> load)]
%   outputs:
%     vv  (3x1, V) phase voltages of the VSG converter (average model)
%     vd  (3x1, V) internal EMF of the diesel synchronous generator
%     il  (3x1, A) current reference of the grid-following/load injection
%     mon (22x1) logged signals; columns 1-13 match the RMS trace of the MATLAB/Python model:
%       t, df_hz, rocof_hz_s, p_vsg_mw, p_bess_mw, p_diesel_mw, soc, H, D, alpha, p_set_mw,
%       headroom_mw, sat_mw, then V_bus_pu, Q_vsg_mvar, P_diesel_elec_mw, P_load_meas_mw,
%       P_load_ref_mw, i_sign, ccs_sign, df_pll_raw_hz, df_diesel_rotor_hz
%
%   Physics and control laws mirror vsgrl_advance.m / vsgrl_episode.m, except that the
%   network is solved by the circuit simulator instead of the algebraic RMS equations:
%     * VSG: swing equation 2H dw/dt = P_set - P_meas - D dw on MEASURED converter power, with a
%       converter power limiter (headroom) acting on the angle, and bus-voltage regulation;
%     * diesel: EMF behind reactance, swing equation, governor + engine lag, droop + AGC;
%     * frequency is measured with a synchronous-reference-frame PLL on the bus voltage.
%#codegen
persistent k thv dwv thd dwd pgov pd xagc thp xp fm rm pset ppvs soc pw Evi
persistent Happ Dapp Aapp have_app isgn csgn evi lstep Pd_f Pl_f Vf
if isempty(k)
    k = 0;  thv = P.th_v0;  dwv = 0;  thd = P.th_d0;  dwd = 0;
    pgov = P.pd0;  pd = P.pd0;  xagc = 0;  thp = 0;  xp = 0;  fm = 0;  rm = 0;
    pset = 0;  ppvs = 0;  soc = P.soc0;  pw = P.p_w0;  Evi = 0;
    Happ = P.nom(1);  Dapp = P.nom(2);  Aapp = P.nom(3);  have_app = false;
    isgn = 1;  csgn = 1;  evi = 1;  lstep = 0;  Pd_f = 0;  Pl_f = 0;  Vf = 1;
end
Ts = P.Ts;  w0 = P.w0;
t = k * Ts;  tep = t - P.Tw;  kep = k - round(P.Tw / Ts);

% ---------------- measurements (pu of S_base) ----------------
v = meas(1:3);
iv = isgn * meas(4:6);  id = isgn * meas(7:9);  ilm = isgn * meas(10:12);
Pv_tot = (v' * iv) / P.Sb_VA;
Pd_e = (v' * id) / P.Sb_VA;
Pl = (v' * ilm) / P.Sb_VA;
Qv = ((v(2) - v(3)) * iv(1) + (v(3) - v(1)) * iv(2) + (v(1) - v(2)) * iv(3)) / sqrt(3) / P.Sb_VA;
s2 = v' * v;
Vpk_meas = sqrt(2/3 * s2);
Vpu = Vpk_meas / P.Vpk;

% ---------------- SRF-PLL on the bus voltage ----------------
valpha = (2/3) * (v(1) - 0.5 * v(2) - 0.5 * v(3));
vbeta = (2/3) * (sqrt(3)/2) * (v(2) - v(3));          % v_a = V sin(theta): v_alpha = V sin, v_beta = -V cos
err = (valpha * cos(thp) + vbeta * sin(thp)) / max(Vpk_meas, 0.1 * P.Vpk);
wp = w0 + P.pll_kp * err + xp;
xp = xp + Ts * P.pll_ki * err;
thp = mod(thp + Ts * wp, 2*pi);
dwp = (wp - w0) / w0;                                  % bus frequency deviation (pu), unfiltered
Vf = Vf + Ts / 0.005 * (Vpu - Vf);                     % filtered voltage magnitude (5 ms)

% net power absorbed by the grid-following/load injection (pu)
Pcs = 0;
hi = 0;  lo = 0;  sat = 0;  head = 0;  Pv = Pv_tot - P.pb0;
if tep < 0
    % -------- warm-up: sources at their initial EMF, rotating at w0; controllers frozen --------
    Pcs = P.load0 - P.p_w0 - P.pv_base - P.P_sh;
    thv = mod(thv + Ts * w0, 2*pi);  thd = mod(thd + Ts * w0, 2*pi);
    Ev = P.E_v0;
    Pd_f = Pd_f + Ts / 0.01 * (Pd_e - Pd_f);
    Pl_f = Pl_f + Ts / 0.01 * (Pl - Pl_f);
    if k == P.k_detect
        % measurement-sign check: the diesel must be exporting (pd0 > 0)
        if Pd_f < 0
            isgn = -isgn;  Pl_f = -Pl_f;
        end
        % the injection must absorb power with the commanded sign
        if Pl_f * Pcs < 0
            csgn = -csgn;
        end
    end
    fm = 0;  rm = 0;
else
    % ---------------- exogenous inputs (same noise sequences as the RMS model) ----------------
    j = min(floor(kep / P.n_noise) + 1, numel(P.turb));
    vw = P.ws * (1 + P.TI * P.turb(j));
    pw_t = min(wind_power(P, max(vw, 0)) / P.Sb_MW, P.wind_cap);
    ld = P.load0 * (1 + P.load_noise * P.lnoise(j));
    while evi <= 3 && tep >= P.ev_t(evi)
        lstep = lstep + P.ev_p(evi);  evi = evi + 1;
    end
    ld = ld + lstep;
    Pcs = ld + P.DL * P.load0 * fm - pw - P.pv_base - P.P_sh;

    % ---------------- converter limits (headroom) ----------------
    [dis, ch] = bess_limits(P, soc);
    hi = dis - P.pb0 + ppvs;
    lo = -(ch + P.pb0) + ppvs;
    if fm <= 0, head = max(dis - P.pb0, 0) + P.h_pv; else, head = max(ch + P.pb0, 0) + P.pv_base; end

    % ---------------- 50 ms decision: (H, D, alpha) ----------------
    if mod(kep, P.n_agent) == 0
        [Happ, Dapp, Aapp] = decide(P, head, fm, rm, Pv, dwv - dwd, dis, ch, soc, pw, pd, ...
                                    Happ, Dapp, Aapp, have_app);
        have_app = true;
    end

    % ---------------- VSG: swing equation on measured power + power limiter ----------------
    exc = max(Pv - hi, 0) - max(lo - Pv, 0);
    sat = abs(exc);
    dwv = dwv + Ts * (pset - Pv - Dapp * dwv) / (2 * max(Happ, 1e-3));
    if exc ~= 0
        dwv = fm;                                      % anti-windup: virtual rotor follows the bus
    end
    thv = mod(thv + Ts * (w0 * (1 + dwv) - P.K_lim * exc), 2*pi);
    Evi = Evi + Ts * P.Ki_v * (1 - Vpu);               % slow bus-voltage regulation
    Ev = P.E_v0 + Evi;

    % ---------------- PV share of the VSG power, BESS secondary control ----------------
    pv_tgt = min(max(Aapp * Pv, -P.pv_base), P.h_pv);
    ppvs = ppvs + Ts * (pv_tgt - ppvs) / P.Tpv;
    pset = min(max(pset - Ts * P.Ki_b * fm, lo), hi);

    % ---------------- diesel: swing, governor (droop + AGC), engine ----------------
    dwd = dwd + Ts * (pd - Pd_e - P.D_d * (dwd - dwp)) / (2 * P.H_d);
    thd = mod(thd + Ts * w0 * (1 + dwd), 2*pi);
    p_ref = P.pd0 - P.inv_R * fm + xagc;
    xagc = xagc - Ts * P.Ki * fm;
    pgov = min(max(pgov + Ts * (p_ref - pgov) / P.Tg, 0), P.Pd_rat);
    dpd = min(max((pgov - pd) / P.Te, -P.ramp), P.ramp);
    pd = min(max(pd + Ts * dpd, 0), P.Pd_rat);

    % ---------------- wind rotor smoothing, BESS energy ----------------
    pw = pw + Ts * (pw_t - pw) / P.Trot;
    pb_mw = (P.pb0 + Pv - ppvs) * P.Sb_MW;
    if pb_mw >= 0
        soc = soc - pb_mw / P.eta_d / P.Eb * Ts / 3600;
    else
        soc = soc - pb_mw * P.eta_c / P.Eb * Ts / 3600;
    end

    % ---------------- frequency measurement (same 20 ms filter as the RMS model) ----------------
    rm = (dwp - fm) / P.Tf;
    fm = fm + Ts * rm;
end

% ---------------- source voltages and injection current ----------------
ph = [0; -2*pi/3; 2*pi/3];
vv = Ev * P.Vpk * sin(thv + ph);
vd = P.E_d0 * P.Vpk * sin(thd + ph);
% grid-following injection: sinusoidal current synchronised to the PLL (unity power factor),
% amplitude from the filtered voltage magnitude so that it absorbs Pcs (constant power)
Iamp = Pcs * P.Sb_VA / (1.5 * P.Vpk * max(Vf, 0.5));
il = csgn * Iamp * sin(thp + ph);
pb_out = (P.pb0 + Pv - ppvs) * P.Sb_MW;
mon = [tep; fm * P.f0; rm * P.f0; Pv * P.Sb_MW; pb_out; pd * P.Sb_MW; soc; Happ; Dapp; Aapp; ...
       pset * P.Sb_MW; head * P.Sb_MW; sat * P.Sb_MW; Vpu; Qv * P.Sb_MW; Pd_e * P.Sb_MW; Pl * P.Sb_MW; ...
       Pcs * P.Sb_MW; isgn; csgn; dwp * P.f0; dwd * P.f0];
k = k + 1;
end

% =====================================================================================
function [H, D, A] = decide(P, head, fm, rm, Pv, dfv, dis, ch, soc, pw, pd, Ha, Da, Aa, have_app)
% (H, D, alpha) for the next 50 ms: baseline or RL policy, rate limit, feasibility projection.
% Mirrors vsgrl_episode.m, vsgrl_headroom_bounds.m, vsgrl_build_obs.m and vsgrl_policy.m.
if P.mode == 3, hc = P.pol_hc; else, hc = P.hc; end
if hc > 0
    d_ub = min(P.d_max, max(P.d_min, head / P.f_band));
    h_ub = min(P.h_max, max(P.h_min, head / (2 * P.rocof_lim)));
else
    d_ub = P.d_max;  h_ub = P.h_max;
end
if have_app
    app = [Ha; Da; Aa];
else
    app = P.nom;
end
if P.mode == 3
    h_up = max(dis - P.pb0, 0) + P.h_pv;
    h_dn = max(ch + P.pb0, 0) + P.pv_base;
    Pd = P.Pd_rat;
    obs = [fm * P.f0 / P.f_target;  rm * P.f0 / P.rocof_limit_hz;  Pv / 0.25;  dfv * P.f0 / 0.1;
           h_up / 0.3;  h_dn / 0.3;  P.h_pv / 0.1;  (soc - 0.5) / 0.4;  pw * P.Sb_MW / 1.0;
           P.pv_mpp * P.Sb_MW / 0.8;  pd / Pd;  (Pd - pd) / Pd;  P.load0 * P.Sb_MW / 1.2;
           2 * app(1) / P.h_max - 1;  2 * app(2) / P.d_max - 1;  2 * app(3) - 1];
    obs = min(max(obs, -10), 10);
    x = max(P.W1 * obs + P.b1, 0);
    x = max(P.W2 * x + P.b2, 0);
    a = min(max(tanh(P.W3 * x + P.b3), -1), 1);
    if P.pol_res > 0
        par = [resid(a(1), P.pol_nom(1), P.h_min, h_ub); resid(a(2), P.pol_nom(2), P.d_min, d_ub);
               resid(a(3), P.pol_nom(3), P.a_min, P.a_max)];
    else
        par = [P.h_min + 0.5 * (a(1) + 1) * (h_ub - P.h_min); P.d_min + 0.5 * (a(2) + 1) * (d_ub - P.d_min);
               P.a_min + 0.5 * (a(3) + 1) * (P.a_max - P.a_min)];
    end
    enforce = P.pol_hc > 0;
else
    par = [P.H_fix; P.D_fix; P.A_fix];
    if P.mode == 2
        par(1) = min(par(1), h_ub);  par(2) = min(par(2), d_ub);
        enforce = P.hc > 0;
    else
        enforce = false;
    end
    par(1) = min(max(par(1), P.h_min), P.h_max);
    par(2) = min(max(par(2), P.d_min), P.d_max);
end
if P.param_tau > 0 && have_app                    % rate limit (tau = 0.25 s) ...
    kf = min(P.agent_dt / P.param_tau, 1);
    par = app + kf * (par - app);
end
if enforce                                        % ... then feasibility before smoothness
    par(1) = min(par(1), h_ub);  par(2) = min(par(2), d_ub);
end
H = par(1);  D = par(2);  A = par(3);
end

function y = resid(a, nominal, lo, hi)
nominal = min(max(nominal, lo), hi);
if a >= 0
    y = nominal + a * (hi - nominal);
else
    y = nominal + a * (nominal - lo);
end
end

function [dis, ch] = bess_limits(P, soc)
dis = P.Pb_max * min(max((soc - P.soc_min) / P.soc_taper, 0), 1);
ch = P.Pb_max * min(max((P.soc_max - soc) / P.soc_taper, 0), 1);
end

function Pw = wind_power(P, v)
v = v * (P.rho / 1.225)^(1/3);
if v < P.w_ci || v >= P.w_co
    Pw = 0;
elseif v >= P.w_vr
    Pw = P.w_rated;
else
    Pw = P.w_rated * (v^3 - P.w_ci^3) / (P.w_vr^3 - P.w_ci^3);
end
end
