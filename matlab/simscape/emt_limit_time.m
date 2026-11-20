function T = emt_limit_time(resdir)
%EMT_LIMIT_TIME  Time the BESS power is held at its limit, averaged model vs EMT, from saved traces.
%   T = emt_limit_time            reads matlab/simscape/results/emt_traces_sc*.mat
%   T = emt_limit_time(resdir)    reads the traces in resdir (e.g. a returned Simscape results folder)
%   Writes <resdir>/limit_time.csv (controller, scenario, rms_limit_s, emt_limit_s) and prints means.
%   Same definition as limit_s in vsgrl/metrics.py and matlab/sim/vsgrl_metrics.m: trace samples at
%   which the BESS power is within 0.1 % of rating of its SoC-tapered discharge or charge limit.
here = fileparts(mfilename('fullpath'));  if isempty(here), here = pwd; end
if nargin < 1, resdir = fullfile(here, 'results'); end
root = fileparts(here);  addpath(fullfile(root, 'sim'));
p = load(fullfile(root, 'export', 'vsgrl_params.mat'));
C = vsgrl_init(p);
f = dir(fullfile(resdir, 'emt_traces_sc*.mat'));
rows = {};
for i = 1:numel(f)
    k = sscanf(f(i).name, 'emt_traces_sc%d.mat');
    S = load(fullfile(resdir, f(i).name));
    names = fieldnames(S.TR);
    for j = 1:numel(names)
        r = S.TR.(names{j});
        rows(end + 1, :) = {names{j}, k, lim_time(C, r.rms), lim_time(C, r.emt(r.emt(:, 1) >= -1e-9, :))}; %#ok<AGROW>
    end
end
fid = fopen(fullfile(resdir, 'limit_time.csv'), 'w');
fprintf(fid, 'controller,scenario,rms_limit_s,emt_limit_s\n');
for r = 1:size(rows, 1)
    fprintf(fid, '%s,%d,%.4f,%.4f\n', rows{r, :});
end
fclose(fid);
T = rows;
c = unique(rows(:, 1));
for j = 1:numel(c)
    m = strcmp(rows(:, 1), c{j});
    a = cell2mat(rows(m, 3));  b = cell2mat(rows(m, 4));
    fprintf('%-15s time at BESS limit: averaged %.3f s, EMT %.3f s per episode (%d scenarios)\n', ...
            c{j}, mean(a), mean(b), sum(m));
end
end

function s = lim_time(C, tr)
t = tr(:, 1);  dt = median(diff(t));
pb = tr(:, 5);  soc = tr(:, 7);  pbmax = C.Pb_max * C.Sb;
dis = pbmax * min(max((soc - C.soc_min) / C.soc_taper, 0), 1);
chg = pbmax * min(max((C.soc_max - soc) / C.soc_taper, 0), 1);
tol = 1e-3 * pbmax;
s = sum(pb >= dis - tol | pb <= -chg + tol) * dt;
end
