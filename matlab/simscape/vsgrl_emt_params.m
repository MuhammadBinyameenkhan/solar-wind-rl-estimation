function PRM = vsgrl_emt_params(C, p, sc, ctrl, pol)
%VSGRL_EMT_PARAMS  Parameter struct for the circuit-level (EMT) model of one scenario.
%   C    : constants from vsgrl_init(p)          p  : struct from export/vsgrl_params.mat
%   sc   : scenario struct (as in run_matlab_validation.m)
%   ctrl : struct('type', 'fixed'|'feasible'|'policy', 'H', .., 'D', .., 'alpha', ..)
%   pol  : exported actor (export/vsgrl_policy_val.mat), needed for type 'policy'
%
%   Network (400 V, 50 Hz, S_base = 2 MVA), all three-phase, grounded star:
%     VSG converter (average model) --R_v + jX_v-- bus --R_d + jX_d-- diesel SG (EMF behind reactance)
%     bus -- shunt resistance (part of the load) and a controlled current source that absorbs
%            load - wind - PV base power (grid-following units and constant-power load).
%   The coupling reactances are chosen so that the synchronising coefficients equal those of the
%   RMS model (X_v = 1/K_s, X_d = 1/K_d), so any difference comes from what the RMS model neglects:
%   network electromagnetics, the E*V*cos(delta) nonlinearity, voltage control, the PLL and the
%   converter power limiter acting on measured power.
S0 = vsgrl_reset(C, sc);                         % same EMS dispatch as the RMS model
PRM = struct();
% --- solver / timing
PRM.Ts = 100e-6;                                 % EMT time step (s)
PRM.Tw = 0.5;                                    % warm-up before the episode starts (s)
PRM.T_ep = p.env_episode_s;
PRM.n_agent = round(C.agent_dt / PRM.Ts);        % 50 ms decision interval in EMT steps
PRM.n_noise = round(C.dt / PRM.Ts);              % noise sequences are given per 2 ms
PRM.k_detect = round(0.2 / PRM.Ts);              % measurement-sign check during warm-up
% --- electrical base and network
PRM.f0 = C.f0;  PRM.w0 = C.w0;
PRM.V_LL = 400;  PRM.Sb_VA = C.Sb * 1e6;  PRM.Sb_MW = C.Sb;
PRM.Vpk = sqrt(2/3) * PRM.V_LL;                  % phase peak voltage at 1 pu
Zb = PRM.V_LL^2 / PRM.Sb_VA;
PRM.X_v = 1 / C.Ks;  PRM.X_d = 1 / C.Kd;  PRM.XR = 10;
PRM.R_v_ohm = PRM.X_v / PRM.XR * Zb;  PRM.L_v_H = PRM.X_v * Zb / PRM.w0;
PRM.R_d_ohm = PRM.X_d / PRM.XR * Zb;  PRM.L_d_H = PRM.X_d * Zb / PRM.w0;
PRM.P_sh = 0.02;                                 % shunt resistive load at 1 pu voltage (pu)
PRM.R_sh_ohm = PRM.V_LL^2 / (PRM.P_sh * PRM.Sb_VA);
% initial source EMFs for 1 pu bus voltage, unity power factor at the bus
Ev = 1 + complex(PRM.X_v / PRM.XR, PRM.X_v) * S0.pb0;
Ed = 1 + complex(PRM.X_d / PRM.XR, PRM.X_d) * S0.pd0;
PRM.E_v0 = abs(Ev);  PRM.th_v0 = angle(Ev);
PRM.E_d0 = abs(Ed);  PRM.th_d0 = angle(Ed);
% --- PLL, power limiter, voltage control
PRM.pll_kp = 2 * 0.7 * (2*pi*20);  PRM.pll_ki = (2*pi*20)^2;   % 20 Hz SRF-PLL (rad/s per pu error)
PRM.K_lim = 100;                                 % converter power limiter (rad/s per pu excess)
PRM.Ki_v = 10;                                   % VSG voltage regulation (pu EMF / s per pu error)
% --- plant constants (same as the RMS model)
f = {'H_d','D_d','inv_R','Tg','Te','ramp','Pd_rat','Ki','Ki_b','Pb_max','Eb','soc_min','soc_max', ...
     'soc_taper','eta_c','eta_d','Tpv','TI','Trot','w_rated','w_ci','w_vr','w_co','DL','load_noise', ...
     'Tf','h_min','h_max','d_min','d_max','agent_dt','param_tau','f_band'};
for i = 1:numel(f), PRM.(f{i}) = C.(f{i}); end
PRM.rocof_lim = p.system_grid_code_rocof_limit_hz_s / C.f0;
PRM.hc = double(p.env_headroom_constraint > 0);
% --- scenario: operating point from the EMS dispatch, events and noise
PRM.ws = sc.ws_hub_ms;  PRM.rho = sc.rho_kgm3;
PRM.load0 = S0.load0;  PRM.pb0 = S0.pb0;  PRM.pd0 = S0.pd0;  PRM.pv_base = S0.pv_base;
PRM.h_pv = S0.h_pv;  PRM.pv_mpp = S0.pv_mpp;  PRM.wind_cap = S0.wind_cap;  PRM.p_w0 = S0.p_w0;
PRM.soc0 = sc.soc0;
ev_t = inf(3, 1);  ev_p = zeros(3, 1);
n = min(numel(S0.ev_t), 3);  ev_t(1:n) = S0.ev_t(1:n);  ev_p(1:n) = S0.ev_p(1:n);
PRM.ev_t = ev_t;  PRM.ev_p = ev_p;
PRM.turb = sc.turb(:);  PRM.lnoise = sc.lnoise(:);
% --- controller
switch ctrl.type
    case 'fixed',    PRM.mode = 1;
    case 'feasible', PRM.mode = 2;
    case 'policy',   PRM.mode = 3;
    otherwise, error('unknown controller type %s', ctrl.type);
end
if PRM.mode < 3
    PRM.H_fix = ctrl.H;  PRM.D_fix = ctrl.D;  PRM.A_fix = ctrl.alpha;
else
    PRM.H_fix = 0;  PRM.D_fix = 0;  PRM.A_fix = 0;
end
PRM.nom = [p.system_vsg_nominal_h_s; p.system_vsg_nominal_d_pu; p.system_vsg_nominal_alpha];
if PRM.mode == 3
    PRM.W1 = pol.W1;  PRM.b1 = pol.b1(:);  PRM.W2 = pol.W2;  PRM.b2 = pol.b2(:);
    PRM.W3 = pol.W3;  PRM.b3 = pol.b3(:);
    PRM.pol_res = double(pol.residual);  PRM.pol_hc = double(pol.headroom_constraint);
    PRM.pol_nom = [pol.nominal_h; pol.nominal_d; pol.nominal_alpha];
    PRM.a_min = pol.alpha_min;  PRM.a_max = pol.alpha_max;
else                                             % same field sizes for every mode (code generation)
    PRM.W1 = zeros(256, 16);  PRM.b1 = zeros(256, 1);  PRM.W2 = zeros(256, 256);  PRM.b2 = zeros(256, 1);
    PRM.W3 = zeros(3, 256);  PRM.b3 = zeros(3, 1);
    PRM.pol_res = 1;  PRM.pol_hc = 1;  PRM.pol_nom = PRM.nom;  PRM.a_min = 0;  PRM.a_max = 1;
end
% observation scaling (vsgrl_build_obs.m)
PRM.f_target = p.system_grid_code_f_target_hz;  PRM.rocof_limit_hz = p.system_grid_code_rocof_limit_hz_s;
end
