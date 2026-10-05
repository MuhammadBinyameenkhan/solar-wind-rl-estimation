%RUN_MATLAB_VALIDATION  MATLAB re-implementation of the study, cross-validated against Python.
%
%   1. In Python:  python scripts/export_matlab_validation.py
%   2. In MATLAB (or GNU Octave), from the matlab/ folder:  run_matlab_validation
%
% Re-simulates the exported test scenarios (same operating points, same wind/load noise) for
% three controllers — tuned fixed VSG, tuned fixed VSG with the headroom projection, and the
% trained TD3 policy — with the independent MATLAB model in matlab/sim/, then compares traces
% and metrics with the Python reference. Outputs: matlab/results/validation_metrics.csv,
% validation_summary.txt and figures (validation_scenario1.png, validation_parity.png).
clear; close all;
if exist('OCTAVE_VERSION', 'builtin')            % GNU Octave: use a headless plotting backend
    try, graphics_toolkit('gnuplot'); catch, end
end
here = fileparts(mfilename('fullpath'));  if isempty(here), here = pwd; end
addpath(here);  addpath(fullfile(here, 'sim'));
ex = fullfile(here, 'export');  outdir = fullfile(here, 'results');
if ~exist(outdir, 'dir'), mkdir(outdir); end
p   = load(fullfile(ex, 'vsgrl_params.mat'));
pol = load(fullfile(ex, 'vsgrl_policy_val.mat'));
V   = load(fullfile(ex, 'vsgrl_validation.mat'));
C = vsgrl_init(p);
nS = numel(V.sc_ws_hub_ms);

% tuned fixed VSG = the residual base of the policy (H, D, alpha)
fixed = struct('type', 'fixed', 'H', pol.nominal_h, 'D', pol.nominal_d, 'alpha', pol.nominal_alpha);
feas  = fixed;  feas.type = 'feasible';
ctrls = {'fixed_tuned', fixed;  'fixed_feasible', feas;  'policy', struct('type', 'policy')};
mnames = {'nadir_hz', 'rocof_max_hz_s', 'bess_energy_kwh', 'infeasible_commit_s', 'saturation_s', 'return'};
tcols = struct('df_hz', 2, 'p_vsg_mw', 4, 'p_bess_mw', 5, 'H_v', 8, 'D_v', 9);   % MATLAB trace columns

rows = {};  err = struct();  dispatch_err = 0;  tic;
for c = 1:size(ctrls, 1)
    cname = ctrls{c, 1};
    for f = fieldnames(tcols)', err.(cname).(f{1}) = []; end
    for i = 1:nS
        sc = struct('ws_hub_ms', V.sc_ws_hub_ms(i), 'rho_kgm3', V.sc_rho_kgm3(i), ...
                    'p_pv_mpp_mw', V.sc_p_pv_mpp_mw(i), 'load_mw', V.sc_load_mw(i), 'soc0', V.sc_soc0(i), ...
                    'events', [V.ev_t(i, :)', V.ev_mw(i, :)'], 'turb', V.turb(i, :), 'lnoise', V.lnoise(i, :));
        [S, M] = vsgrl_episode(C, p, sc, ctrls{c, 2}, pol);
        if c == 1        % dispatch check (operating point) against Python
            dispatch_err = max([dispatch_err, abs(S.pd0*C.Sb - V.py_pd0(i)), abs(S.pb0*C.Sb - V.py_pb0(i)), ...
                                abs(S.load0*C.Sb - V.py_load0(i))]);
        end
        n = min(S.n_tr, sum(~isnan(V.([cname '_df_hz'])(i, :))));
        for f = fieldnames(tcols)'
            py = V.([cname '_' f{1}])(i, 1:n)';  ml = S.trace(1:n, tcols.(f{1}));
            err.(cname).(f{1})(end + 1) = max(abs(py - ml));
        end
        for j = 1:numel(mnames)
            rows(end + 1, :) = {cname, i, mnames{j}, V.([cname '_m_' mnames{j}])(i), M.(mnames{j})}; %#ok<SAGROW>
        end
        if i == 1, S1.(cname) = S; end
    end
    fprintf('%-15s simulated %d scenarios (%.0f s elapsed)\n', cname, nS, toc);
end

% ---- summary -------------------------------------------------------------------------------
fid = fopen(fullfile(outdir, 'validation_summary.txt'), 'w');
for out = [1, fid]
    fprintf(out, '\nMATLAB vs Python cross-validation (%d test scenarios, 30 s, 2-3 events each)\n', nS);
    fprintf(out, 'Operating-point dispatch: max |difference| = %.2e MW\n\n', dispatch_err);
    fprintf(out, '%-15s %12s %12s %12s %10s %10s\n', 'controller', 'max|dDf| Hz', 'max|dPvsg| MW', ...
            'max|dPbess| MW', 'max|dH| s', 'max|dD| pu');
    for c = 1:size(ctrls, 1)
        e = err.(ctrls{c, 1});
        fprintf(out, '%-15s %12.2e %12.2e %12.2e %10.2e %10.2e\n', ctrls{c, 1}, max(e.df_hz), max(e.p_vsg_mw), ...
                max(e.p_bess_mw), max(e.H_v), max(e.D_v));
    end
    fprintf(out, '\n%-15s %-20s %12s %12s %12s\n', 'controller', 'metric (mean)', 'Python', 'MATLAB', 'rel. diff');
    for c = 1:size(ctrls, 1)
        for j = 1:numel(mnames)
            sel = strcmp(rows(:, 1), ctrls{c, 1}) & strcmp(rows(:, 3), mnames{j});
            py = mean(cell2mat(rows(sel, 4)));  ml = mean(cell2mat(rows(sel, 5)));
            fprintf(out, '%-15s %-20s %12.4f %12.4f %11.2f%%\n', ctrls{c, 1}, mnames{j}, py, ml, ...
                    100 * abs(ml - py) / max(abs(py), 1e-9));
        end
    end
end
fclose(fid);

% ---- CSV of all metrics -------------------------------------------------------------------
fid = fopen(fullfile(outdir, 'validation_metrics.csv'), 'w');
fprintf(fid, 'controller,scenario,metric,python,matlab\n');
for r = 1:size(rows, 1)
    fprintf(fid, '%s,%d,%s,%.6f,%.6f\n', rows{r, 1}, rows{r, 2}, rows{r, 3}, rows{r, 4}, rows{r, 5});
end
fclose(fid);

% ---- scenario-1 traces (Python vs MATLAB) as CSV, for plotting anywhere ----------------------
fid = fopen(fullfile(outdir, 'validation_traces_sc1.csv'), 'w');
fprintf(fid, 'controller,t,df_python_hz,df_matlab_hz,pvsg_python_mw,pvsg_matlab_mw\n');
for c = 1:size(ctrls, 1)
    cname = ctrls{c, 1};  S = S1.(cname);  n = S.n_tr;
    for r = 1:n
        fprintf(fid, '%s,%.3f,%.7f,%.7f,%.7f,%.7f\n', cname, S.trace(r, 1), V.([cname '_df_hz'])(1, r), ...
                S.trace(r, 2), V.([cname '_p_vsg_mw'])(1, r), S.trace(r, 4));
    end
end
fclose(fid);

% ---- figures (skipped gracefully where no graphics are available, e.g. headless Octave) -------
try
cols = {[0.165 0.471 0.839], [0.922 0.408 0.204], [0.290 0.227 0.655]};
fig = figure('visible', 'off', 'position', [100 100 760 620]);
labels = {'Fixed VSG (tuned)', 'Fixed VSG + projection', 'TD3 policy'};
for c = 1:3
    cname = ctrls{c, 1};  S = S1.(cname);  n = S.n_tr;  py = V.([cname '_df_hz'])(1, 1:n);
    subplot(3, 1, c);
    plot(S.trace(1:n, 1), py, 'color', [0.6 0.6 0.6], 'linewidth', 3); hold on;
    plot(S.trace(1:n, 1), S.trace(1:n, 2), '--', 'color', cols{c}, 'linewidth', 1.4);
    ylabel('\Deltaf (Hz)'); grid on; title(labels{c});
    legend({'Python', 'MATLAB'}, 'location', 'southeast');
end
xlabel('Time (s)');
print(fig, fullfile(outdir, 'validation_scenario1.png'), '-dpng', '-r150');

fig = figure('visible', 'off', 'position', [100 100 900 300]);
show = {'nadir_hz', 'rocof_max_hz_s', 'bess_energy_kwh'};
for j = 1:3
    subplot(1, 3, j); hold on;
    for c = 1:3
        sel = strcmp(rows(:, 1), ctrls{c, 1}) & strcmp(rows(:, 3), show{j});
        plot(cell2mat(rows(sel, 4)), cell2mat(rows(sel, 5)), 'o', 'color', cols{c}, 'markerfacecolor', cols{c});
    end
    vals = cell2mat(rows(strcmp(rows(:, 3), show{j}), 4:5));     % (MATLAB-compatible: no chained indexing)
    lim = [min(vals(:)), max(vals(:))];
    plot(lim, lim, 'k:'); axis tight; grid on;
    xlabel(['Python ' strrep(show{j}, '_', ' ')]); ylabel('MATLAB');
end
legend(labels, 'location', 'southeast');
print(fig, fullfile(outdir, 'validation_parity.png'), '-dpng', '-r150');
catch figerr
    fprintf('Figures skipped (%s). The CSV files contain all data.\n', figerr.message);
end
fprintf('\nWrote %s\n', outdir);
