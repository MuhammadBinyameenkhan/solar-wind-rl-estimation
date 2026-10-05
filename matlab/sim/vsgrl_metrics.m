function M = vsgrl_metrics(C, S, sc)
%VSGRL_METRICS  Frequency-response metrics from an episode trace (mirrors vsgrl/metrics.py).
tr = S.trace;  t = tr(:, 1);  df = tr(:, 2);
dt = median(diff(t));
ev = sc.events;  ev = ev(~isnan(ev(:, 1)), :);  [~, o] = sort(ev(:, 1));  ev = ev(o, :);
nadirs = [];
for i = 1:size(ev, 1)
    t_e = ev(i, 1);
    if i < size(ev, 1), t_end = ev(i + 1, 1); else, t_end = t(end) + dt; end
    win = t >= t_e & t < t_end;
    if any(win)
        sgn = 1;  if ev(i, 2) < 0, sgn = -1; end
        nadirs(end + 1) = max(-sgn * df(win)); %#ok<AGROW>
    end
end
w = max(round(C.rocof_window_s / dt), 1);
rocof_w = (df(1 + w:end) - df(1:end - w)) / (w * dt);
pb = tr(:, 5);
need = max(tr(:, 9) * C.f_band, 2 * tr(:, 8) * C.r_lim);
M = struct();
M.nadir_hz = max([nadirs, 0]);
M.rocof_max_hz_s = max(abs(rocof_w));
M.bess_energy_kwh = sum(abs(pb - pb(1))) * dt * 1000 / 3600;
M.infeasible_commit_s = sum(need > tr(:, 12) / C.Sb + 1e-6) * dt;
M.saturation_s = sum(tr(:, 13) > 1e-4) * dt;
end
