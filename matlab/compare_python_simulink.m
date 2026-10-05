%COMPARE_PYTHON_SIMULINK  Overlay a Simscape run on the Python reference trace and
% report the metric discrepancies (the validation table of the paper).
%   Expects: export/traces/<ctrl>_s<seed>_sc<k>.csv  (from scripts/export_matlab.py)
%            a Simulink output timeseries struct `simout` with fields t, df_hz, p_vsg_mw
ctrl = 'td3'; seed = 0; k = 0;               % <-- edit
ref = readtable(sprintf('export/traces/%s_s%d_sc%d.csv', ctrl, seed, k));
sim_t = simout.t;  sim_df = simout.df_hz;  sim_p = simout.p_vsg_mw;
df_i = interp1(sim_t, sim_df, ref.t, 'linear', 'extrap');
p_i  = interp1(sim_t, sim_p,  ref.t, 'linear', 'extrap');
w = round(0.1 / median(diff(ref.t)));        % 100 ms RoCoF window, as in vsgrl/metrics.py
roc = @(f) max(abs(f(1+w:end) - f(1:end-w)) / (w * median(diff(ref.t))));
fprintf('Nadir   : Python %.3f Hz | Simulink %.3f Hz\n', max(abs(ref.df_hz)), max(abs(df_i)));
fprintf('RoCoF   : Python %.3f Hz/s | Simulink %.3f Hz/s\n', roc(ref.df_hz), roc(df_i));
fprintf('RMSE Δf : %.4f Hz,  RMSE P_vsg: %.4f MW\n', sqrt(mean((ref.df_hz - df_i).^2)), sqrt(mean((ref.p_vsg_mw - p_i).^2)));
figure; subplot(2,1,1); plot(ref.t, ref.df_hz, ref.t, df_i, '--'); ylabel('\Deltaf (Hz)'); legend('Python RMS','Simscape');
subplot(2,1,2); plot(ref.t, ref.p_vsg_mw, ref.t, p_i, '--'); ylabel('P_{VSG} (MW)'); xlabel('t (s)');
