function mon = vsgrl_emt_bench(PRM, opts)
%VSGRL_EMT_BENCH  Simulink-free EMT test bench: the same three-phase circuit as vsgrl_emt.slx,
%   solved per phase with backward Euler at PRM.Ts, driven by vsgrl_emt_ctrl.m.
%   Used to test the controller (and the measurement-sign detection) without Simulink.
%   opts.T_end       simulated time incl. warm-up (default PRM.Tw + PRM.T_ep)
%   opts.meas_sign   +1/-1: current-measurement convention of the "circuit" (default +1)
%   opts.ccs_sign    +1/-1: orientation of the controlled current source (default +1)
%   opts.decim       logging decimation (default 100 -> every 10 ms, the RMS trace step)
%   Returns mon (n x 22), columns as documented in vsgrl_emt_ctrl.m.
if nargin < 2, opts = struct(); end
T_end = getdef(opts, 'T_end', PRM.Tw + PRM.T_ep);
ms = getdef(opts, 'meas_sign', 1);  cs = getdef(opts, 'ccs_sign', 1);
decim = getdef(opts, 'decim', 100);
clear vsgrl_emt_ctrl                              % reset the persistent controller states
Ts = PRM.Ts;  N = round(T_end / Ts);
gv = 1 / (PRM.L_v_H / Ts + PRM.R_v_ohm);  gd = 1 / (PRM.L_d_H / Ts + PRM.R_d_ohm);
iv = zeros(3, 1);  id = zeros(3, 1);  il = zeros(3, 1);  v = zeros(3, 1);
meas = zeros(12, 1);
mon = zeros(floor(N / decim) + 1, 22);  r = 0;
for n = 0:N - 1
    [ev, ed, il_cmd, m] = vsgrl_emt_ctrl(meas, PRM);
    if mod(n, decim) == 0
        r = r + 1;  mon(r, :) = m';
    end
    il = cs * il_cmd;                               % actual current drawn from the bus
    v = (gv * (PRM.L_v_H / Ts * iv + ev) + gd * (PRM.L_d_H / Ts * id + ed) - il) / (gv + gd + 1 / PRM.R_sh_ohm);
    iv = gv * (PRM.L_v_H / Ts * iv + ev - v);
    id = gd * (PRM.L_d_H / Ts * id + ed - v);
    meas = [v; ms * iv; ms * id; ms * il];
end
mon = mon(1:r, :);
end

function v = getdef(s, f, d)
if isfield(s, f), v = s.(f); else, v = d; end
end
