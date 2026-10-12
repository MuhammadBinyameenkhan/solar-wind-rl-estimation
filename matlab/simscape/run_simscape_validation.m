%RUN_SIMSCAPE_VALIDATION  Circuit-level (EMT) validation of the RMS study model in Simscape Electrical.
%
%   Run from the matlab/simscape folder (MATLAB R2021a or newer, Simulink + Simscape Electrical):
%       run_simscape_validation
%
%   For each selected test scenario and controller (tuned fixed VSG, fixed VSG + headroom
%   projection, trained TD3 policy) it
%     1. builds the operating point exactly as the RMS model (same EMS dispatch, events, noise),
%     2. simulates the three-phase 400 V microgrid in vsgrl_emt.slx (built automatically on the
%        first run by build_vsgrl_simscape.m) for 0.5 s warm-up + 30 s,
%     3. simulates the same scenario with the RMS model (matlab/sim, identical to Python),
%     4. compares frequency, VSG power and the paper metrics.
%   Outputs in matlab/simscape/results/: simscape_metrics.csv, simscape_summary.txt,
%   simscape_scenario<k>.png, simscape_parity.png, emt_traces_sc<k>.mat
%
%   USE_SIMULINK = false runs the identical circuit with the script-only solver
%   vsgrl_emt_bench.m instead (no Simulink needed; slower; useful as a cross-check).
clear; close all;
SCENARIOS = 1;            % test scenarios to simulate (1..12); start small, then use 1:12
USE_SIMULINK = true;      % false: script-only EMT solver (vsgrl_emt_bench.m)

here = fileparts(mfilename('fullpath'));  if isempty(here), here = pwd; end
cd(here);                                  % Simulink writes compiled code (slprj/) to the current folder
root = fileparts(here);                    % the matlab/ folder
addpath(here);  addpath(root);  addpath(fullfile(root, 'sim'));
outdir = fullfile(here, 'results');  if ~exist(outdir, 'dir'), mkdir(outdir); end
ex = fullfile(root, 'export');
p   = load(fullfile(ex, 'vsgrl_params.mat'));
pol = load(fullfile(ex, 'vsgrl_policy_val.mat'));
V   = load(fullfile(ex, 'vsgrl_validation.mat'));
C = vsgrl_init(p);
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct, USE_SIMULINK = false; end

fixed = struct('type', 'fixed', 'H', pol.nominal_h, 'D', pol.nominal_d, 'alpha', pol.nominal_alpha);
feas = fixed;  feas.type = 'feasible';
ctrls = {'fixed_tuned', fixed;  'fixed_feasible', feas;  'policy', struct('type', 'policy')};
labels = {'Fixed VSG (tuned)', 'Fixed VSG + projection', 'TD3 policy'};
mnames = {'nadir_hz', 'rocof_max_hz_s', 'rocof_500ms_hz_s', 'rotor_rocof_hz_s', 'bess_energy_kwh', ...
          'infeasible_commit_s', 'saturation_s'};
rows = {};  built = false;  tic;
for i = SCENARIOS
    sc = struct('ws_hub_ms', V.sc_ws_hub_ms(i), 'rho_kgm3', V.sc_rho_kgm3(i), ...
                'p_pv_mpp_mw', V.sc_p_pv_mpp_mw(i), 'load_mw', V.sc_load_mw(i), 'soc0', V.sc_soc0(i), ...
                'events', [V.ev_t(i, :)', V.ev_mw(i, :)'], 'turb', V.turb(i, :), 'lnoise', V.lnoise(i, :));
    TR = struct();
    for c = 1:size(ctrls, 1)
        cname = ctrls{c, 1};
        PRM = vsgrl_emt_params(C, p, sc, ctrls{c, 2}, pol);
        % ---- EMT simulation
        if USE_SIMULINK
            assignin('base', 'PRM', PRM);
            if ~built
                if ~exist(fullfile(here, 'vsgrl_emt.slx'), 'file')
                    build_vsgrl_simscape(PRM);
                end
                load_system(fullfile(here, 'vsgrl_emt.slx'));
                built = true;
            end
            out = sim('vsgrl_emt');
            if isa(out, 'Simulink.SimulationOutput'), mon = out.get('emt_mon'); else, mon = evalin('base', 'emt_mon'); end
        else
            mon = vsgrl_emt_bench(PRM);
        end
        if c == 1 && i == SCENARIOS(1)          % plausibility check of the first run
            w = mon(:, 1) < 0 & mon(:, 1) > -0.05;
            fprintf(['\nCheck (end of warm-up): bus voltage %.3f pu (expect ~1), diesel %.3f MW (expect %.3f),\n' ...
                     '  load injection %.3f MW (reference %.3f), detected signs: current %+d, injection %+d\n\n'], ...
                    mean(mon(w, 14)), mean(mon(w, 16)), PRM.pd0 * PRM.Sb_MW, mean(mon(w, 17)), mean(mon(w, 18)), ...
                    mon(end, 19), mon(end, 20));
        end
        % ---- RMS reference (identical to Python)
        [S, M] = vsgrl_episode(C, p, sc, ctrls{c, 2}, pol);
        Se = S;  Se.trace = mon(mon(:, 1) >= -1e-9, 1:13);
        Me = vsgrl_metrics(C, Se, sc);
        Me.rocof_500ms_hz_s = vsgrl_rocof_window(Se.trace(:, 1), Se.trace(:, 2), 0.5);
        M.rocof_500ms_hz_s = vsgrl_rocof_window(S.trace(:, 1), S.trace(:, 2), 0.5);
        Me.rotor_rocof_hz_s = vsgrl_rocof_window(Se.trace(:, 1), mon(mon(:, 1) >= -1e-9, 22), 0.1);
        M.rotor_rocof_hz_s = NaN;               % (RMS: rotor speed not in the trace)
        for j = 1:numel(mnames)
            rows(end + 1, :) = {cname, i, mnames{j}, M.(mnames{j}), Me.(mnames{j})}; %#ok<SAGROW>
        end
        n = min(size(S.trace, 1), size(Se.trace, 1));
        rmse = sqrt(mean((S.trace(1:n, 2) - Se.trace(1:n, 2)).^2));
        rows(end + 1, :) = {cname, i, 'rmse_df_hz', 0, rmse}; %#ok<SAGROW>
        TR.(cname) = struct('rms', S.trace, 'emt', mon);
        fprintf('scenario %2d  %-15s nadir RMS %.3f / EMT %.3f Hz   RoCoF(100 ms) %.2f / %.2f Hz/s   RMSE(df) %.3f Hz   [%4.0f s]\n', ...
                i, cname, M.nadir_hz, Me.nadir_hz, M.rocof_max_hz_s, Me.rocof_max_hz_s, rmse, toc);
    end
    save(fullfile(outdir, sprintf('emt_traces_sc%d.mat', i)), 'TR');
    % ---- figure per scenario: frequency and VSG power, RMS vs EMT
    try
        fig = figure('Position', [80 80 900 640], 'Name', sprintf('Scenario %d', i));
        cols = {[0.165 0.471 0.839], [0.922 0.408 0.204], [0.290 0.227 0.655]};
        for c = 1:3
            T = TR.(ctrls{c, 1});  e = T.emt(T.emt(:, 1) >= 0, :);
            subplot(3, 2, 2*c - 1);
            plot(T.rms(:, 1), T.rms(:, 2), 'Color', [0.6 0.6 0.6], 'LineWidth', 2.5); hold on;
            plot(e(:, 1), e(:, 2), '--', 'Color', cols{c}, 'LineWidth', 1.2);
            grid on; ylabel('\Deltaf (Hz)'); title(labels{c});
            if c == 1, legend({'RMS model', 'Simscape EMT'}, 'Location', 'southeast'); end
            subplot(3, 2, 2*c);
            plot(T.rms(:, 1), T.rms(:, 4), 'Color', [0.6 0.6 0.6], 'LineWidth', 2.5); hold on;
            plot(e(:, 1), e(:, 4), '--', 'Color', cols{c}, 'LineWidth', 1.2);
            grid on; ylabel('P_{VSG} (MW)'); title(labels{c});
        end
        subplot(3, 2, 5); xlabel('Time (s)');  subplot(3, 2, 6); xlabel('Time (s)');
        print(fig, fullfile(outdir, sprintf('simscape_scenario%d.png', i)), '-dpng', '-r150');
    catch figerr
        fprintf('Figure skipped (%s)\n', figerr.message);
    end
end

% ---------------- summary ----------------
fid = fopen(fullfile(outdir, 'simscape_metrics.csv'), 'w');
fprintf(fid, 'controller,scenario,metric,rms,emt\n');
for r = 1:size(rows, 1)
    fprintf(fid, '%s,%d,%s,%.6f,%.6f\n', rows{r, :});
end
fclose(fid);
fid = fopen(fullfile(outdir, 'simscape_summary.txt'), 'w');
allm = [mnames, {'rmse_df_hz'}];
if USE_SIMULINK, solver_name = 'Simulink/Simscape Electrical'; else, solver_name = 'script-only EMT bench'; end
for out = [1, fid]
    fprintf(out, '\nRMS model vs Simscape EMT (%d scenarios: %s; solver: %s)\n', numel(SCENARIOS), ...
            mat2str(SCENARIOS), solver_name);
    fprintf(out, '%-15s %-20s %10s %10s %10s\n', 'controller', 'metric (mean)', 'RMS', 'EMT', 'diff');
    for c = 1:size(ctrls, 1)
        for j = 1:numel(allm)
            sel = strcmp(rows(:, 1), ctrls{c, 1}) & strcmp(rows(:, 3), allm{j});
            a = mean(cell2mat(rows(sel, 4)));  b = mean(cell2mat(rows(sel, 5)));
            if strcmp(allm{j}, 'rmse_df_hz') || isnan(a) || abs(a) < 1e-6
                if isnan(a) || strcmp(allm{j}, 'rmse_df_hz'), as = '-'; else, as = sprintf('%.4f', a); end
                fprintf(out, '%-15s %-20s %10s %10.4f\n', ctrls{c, 1}, allm{j}, as, b);
            else
                fprintf(out, '%-15s %-20s %10.4f %10.4f %9.1f%%\n', ctrls{c, 1}, allm{j}, a, b, ...
                        100 * (b - a) / max(abs(a), 1e-9));
            end
        end
    end
end
fclose(fid);
try
    fig = figure('Position', [80 80 1000 300], 'Name', 'Parity');
    show = {'nadir_hz', 'rocof_500ms_hz_s', 'bess_energy_kwh'};
    cols = {[0.165 0.471 0.839], [0.922 0.408 0.204], [0.290 0.227 0.655]};
    for j = 1:3
        subplot(1, 3, j); hold on;
        for c = 1:3
            sel = strcmp(rows(:, 1), ctrls{c, 1}) & strcmp(rows(:, 3), show{j});
            plot(cell2mat(rows(sel, 4)), cell2mat(rows(sel, 5)), 'o', 'Color', cols{c}, 'MarkerFaceColor', cols{c});
        end
        vals = cell2mat(rows(strcmp(rows(:, 3), show{j}), 4:5));
        lim = [min(vals(:)), max(vals(:))];
        plot(lim, lim, 'k:'); grid on; axis tight;
        xlabel(['RMS ' strrep(show{j}, '_', ' ')]); ylabel('Simscape EMT');
    end
    legend(labels, 'Location', 'southeast');
    print(fig, fullfile(outdir, 'simscape_parity.png'), '-dpng', '-r150');
catch figerr
    fprintf('Figure skipped (%s)\n', figerr.message);
end
fprintf('\nWrote %s\n', outdir);

