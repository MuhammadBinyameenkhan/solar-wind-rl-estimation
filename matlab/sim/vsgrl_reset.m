function S = vsgrl_reset(C, sc)
%VSGRL_RESET  Operating point (economic dispatch incl. EMS) and initial states for one scenario.
%   sc fields: ws_hub_ms, rho_kgm3, p_pv_mpp_mw, load_mw, soc0, events (k x 2: time_s, MW),
%              turb, lnoise (noise sequences, one value per 2 ms step).  Mirrors Microgrid.reset.
Sb = C.Sb;
p_w_av = vsgrl_wind_power(C, sc.ws_hub_ms, sc.rho_kgm3) / Sb;
mpp = sc.p_pv_mpp_mw / Sb;
pv_base = (1 - C.deload) * mpp;
headroom = C.deload * mpp;
load = sc.load_mw / Sb;
soc = sc.soc0;
[dis_max, ch_max] = vsgrl_bess_limits(C, soc);

wind_cap = p_w_av;  pb0 = 0;  load_clipped = 0;
residual = load - p_w_av - pv_base;
if residual < C.Pd_min                          % RES surplus
    cut = C.Pd_min - residual;
    if C.ems_on                                  % EMS: charge the BESS first
        chg = min(cut, C.ems_max * ch_max);
        pb0 = -chg;  cut = cut - chg;
    end
    wcut = min(cut, p_w_av);  wind_cap = p_w_av - wcut;  cut = cut - wcut;
    if cut > 0
        pcut = min(cut, pv_base);  pv_base = pv_base - pcut;  headroom = headroom + pcut;  cut = cut - pcut;
    end
    if cut > 0
        load = load + cut;  load_clipped = -cut;
    end
    residual = C.Pd_min + pb0;
end
if C.ems_on, target = C.ems_target * C.Pd_rat; frac = C.ems_max; else, target = C.Pd_disp_max; frac = 0.6; end
if residual > target                            % deficit above the diesel target
    deficit = residual - target;
    pb0 = min(deficit, frac * dis_max);
    rest = deficit - pb0;
    extra_d = min(rest, C.Pd_disp_max - target);
    rest = rest - extra_d;
    load = load - rest;  load_clipped = rest;
    residual = target + extra_d + pb0;
end
pd0 = residual - pb0;

S = struct();
S.sc = sc;  S.t = 0;  S.k = 0;
S.p_w_av0 = p_w_av;  S.wind_cap = wind_cap;  S.pv_base = pv_base;  S.h_pv = headroom;  S.pv_mpp = mpp;
S.load0 = load;  S.pb0 = pb0;  S.pd0 = pd0;  S.load_clipped = load_clipped;
ev = sc.events;  ev = ev(~isnan(ev(:, 1)), :);  [~, o] = sort(ev(:, 1));  ev = ev(o, :);
S.ev_t = ev(:, 1);  S.ev_p = ev(:, 2) / Sb;  S.ev_i = 1;  S.load_step = 0;
% states
S.dw_d = 0;  S.dw_v = 0;  S.dw_b = 0;  S.delta = 0;  S.p_vsg = 0;  S.p_pv_s = 0;
S.p_gov = pd0;  S.p_d = pd0;  S.x_agc = 0;  S.p_set = 0;  S.soc = soc;
S.p_w0 = min(p_w_av, wind_cap);  S.p_w = S.p_w0;  S.f_meas = 0;  S.rocof_meas = 0;
% trace buffer: t, df_hz, rocof_hz_s, p_vsg_mw, p_bess_mw, p_diesel_mw, soc, H, D, alpha, p_set_mw, headroom_mw, sat_mw
S.trace = nan(ceil(numel(sc.turb) / C.trace_every), 13);  S.n_tr = 0;
end
