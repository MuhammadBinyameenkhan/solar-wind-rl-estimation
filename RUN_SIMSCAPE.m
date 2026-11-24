%RUN_SIMSCAPE  Simscape Electrical (EMT) validation of Study 2 with the measured EGAT load.
%
%   Requirements: MATLAB R2021a or newer with Simulink and Simscape Electrical
%   (Specialized Power Systems). Open the repository folder in MATLAB and type:  RUN_SIMSCAPE
%
%   Step 1 (about 1 min): MATLAB re-implementation vs the Python results (12 scenarios).
%           Expected: identical for the fixed controllers, TD3 within about 1e-7 Hz.
%   Step 2 (about 1-3 h): three-phase Simscape model, 12 test scenarios x 3 controllers
%           (tuned fixed VSG, fixed VSG + projection, TD3 seed 1 final policy).
%           The model vsgrl_emt.slx is built automatically on the first run.
%   Results: matlab/simscape/results/  (simscape_metricssimscape.csv,
%            simscape_summarysimscape.txt, simscape_scenario<k>.png, simscape_parity.png)
%   Compare with reference_script_solver/ (same circuit solved by a script in Octave).
%   Send back the whole matlab/simscape/results folder (zip it).
%
%   The two scripts below start with "clear", so the package folder is kept in an
%   environment variable rather than in a workspace variable.

setenv('VSGRL_PKG', fileparts(mfilename('fullpath')));
if isempty(getenv('VSGRL_PKG')), setenv('VSGRL_PKG', pwd); end

fprintf('\n=== Step 1: MATLAB vs Python cross-check ===\n');
cd(fullfile(getenv('VSGRL_PKG'), 'matlab'));
run_matlab_validation;

fprintf('\n=== Step 2: Simscape EMT, 12 scenarios x 3 controllers ===\n');
setenv('VSGRL_EMT_SCEN', '[1:12]');     % all twelve validation scenarios
setenv('VSGRL_EMT_TAG', 'simscape');    % output files get the suffix "simscape"
cd(fullfile(getenv('VSGRL_PKG'), 'matlab', 'simscape'));
run_simscape_validation;

cd(getenv('VSGRL_PKG'));
fprintf('\nDone. Please zip and send back: %s\n', fullfile(getenv('VSGRL_PKG'), 'matlab', 'simscape', 'results'));
