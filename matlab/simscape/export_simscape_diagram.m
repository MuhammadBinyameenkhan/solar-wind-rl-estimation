%EXPORT_SIMSCAPE_DIAGRAM  Save the Simscape Electrical model diagram (vsgrl_emt.slx) as image files.
%
%   Run from the matlab/simscape folder (MATLAB R2021a or newer with Simscape Electrical):
%       export_simscape_diagram
%   Builds the model first if vsgrl_emt.slx is not there (build_vsgrl_simscape), then writes
%       results/fig_simscape_model.png  (600 dpi)
%       results/fig_simscape_model.pdf  (vector)
%       results/fig_simscape_model.svg  (vector, editable)
%   and the same three files for the Controller subsystem / MATLAB Function block if it is a
%   subsystem (fig_simscape_controller.*).

here = fileparts(mfilename('fullpath'));
if isempty(here), here = pwd; end
cd(here);
mdl = 'vsgrl_emt';
if ~exist(fullfile(here, [mdl '.slx']), 'file')
    fprintf('Model not found - building it with build_vsgrl_simscape ...\n');
    build_vsgrl_simscape;
end
load_system(mdl);
open_system(mdl);                         % printing needs an open window
set_param(mdl, 'ZoomFactor', 'FitSystem');
outdir = fullfile(here, 'results');
if ~exist(outdir, 'dir'), mkdir(outdir); end

base = fullfile(outdir, 'fig_simscape_model');
print(['-s' mdl], '-dpng', '-r600', [base '.png']);
print(['-s' mdl], '-dpdf', [base '.pdf']);
print(['-s' mdl], '-dsvg', [base '.svg']);
fprintf('Wrote %s.{png,pdf,svg}\n', base);

% controller block, if it can be opened as a diagram
blk = [mdl '/Controller'];
try
    if strcmp(get_param(blk, 'BlockType'), 'SubSystem') && ...
            ~strcmp(get_param(blk, 'SFBlockType'), 'MATLAB Function')
        open_system(blk);
        base = fullfile(outdir, 'fig_simscape_controller');
        print(['-s' blk], '-dpng', '-r600', [base '.png']);
        print(['-s' blk], '-dpdf', [base '.pdf']);
        fprintf('Wrote %s.{png,pdf}\n', base);
    end
catch
    % a MATLAB Function block has no diagram of its own; its code is vsgrl_emt_ctrl.m
end
