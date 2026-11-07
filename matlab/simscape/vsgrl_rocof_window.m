function r = vsgrl_rocof_window(t, f, win)
%VSGRL_ROCOF_WINDOW  Maximum |RoCoF| of signal f(t) over a sliding window of length win (s).
dt = median(diff(t));  w = max(round(win / dt), 1);
r = max(abs(f(1 + w:end) - f(1:end - w)) / (w * dt));
end
