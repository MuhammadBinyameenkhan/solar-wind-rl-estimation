%EXPORT_EMT_TRACES_CSV  Write the RMS and EMT traces of one scenario to CSV (for plotting outside MATLAB).
%   Usage (from matlab/simscape):  k = 1; export_emt_traces_csv
if ~exist('k', 'var'), k = 1; end
here = fileparts(mfilename('fullpath'));  if isempty(here), here = pwd; end
S = load(fullfile(here, 'results', sprintf('emt_traces_sc%d.mat', k)));
fid = fopen(fullfile(here, 'results', sprintf('emt_traces_sc%d.csv', k)), 'w');
fprintf(fid, 'controller,model,t,df_hz,p_vsg_mw\n');
for c = fieldnames(S.TR)'
    T = S.TR.(c{1});
    for r = 1:size(T.rms, 1)
        fprintf(fid, '%s,rms,%.3f,%.6f,%.6f\n', c{1}, T.rms(r, 1), T.rms(r, 2), T.rms(r, 4));
    end
    e = T.emt(T.emt(:, 1) >= 0, :);
    for r = 1:size(e, 1)
        fprintf(fid, '%s,emt,%.3f,%.6f,%.6f\n', c{1}, e(r, 1), e(r, 2), e(r, 4));
    end
end
fclose(fid);
fprintf('wrote emt_traces_sc%d.csv\n', k);
