function mdl = build_vsgrl_simscape(PRM)
%BUILD_VSGRL_SIMSCAPE  Build the circuit-level microgrid model vsgrl_emt.slx (Simscape Electrical,
%   Specialized Power Systems, discrete 100 us). Run from the matlab/simscape folder:
%       build_vsgrl_simscape            % uses a PRM struct from the base workspace if present
%   The model contains only standard blocks plus one MATLAB Function block (vsgrl_emt_ctrl.m):
%
%     VSG converter (3 x Controlled Voltage Source) - RL coupling - V-I meas --+
%                                                                              |-- bus -- shunt R
%     diesel EMF    (3 x Controlled Voltage Source) - RL (X_d)    - V-I meas --+
%                                                                              |
%                                         V-I meas - 3 x Controlled Current Source (load - wind - PV)
%
%   Measurements (bus voltage, three branch currents) go through a Unit Delay to the controller,
%   whose outputs drive the sources. Logged signals: emt_mon (To Workspace).
%   Tested with R2021a. If a step fails, the error message lists the parameter names of the
%   block involved -- send it to the maintainer.
if nargin < 1
    if evalin('base', 'exist(''PRM'', ''var'')'), PRM = evalin('base', 'PRM');
    else, error('Create PRM first (run_simscape_validation does this), or pass it as an argument.'); end
end
mdl = 'vsgrl_emt';
here = fileparts(mfilename('fullpath'));
file = fullfile(here, [mdl '.slx']);
if bdIsLoaded(mdl), close_system(mdl, 0); end
if exist(file, 'file'), delete(file); end
new_system(mdl);  open_system(mdl);
load_system('powerlib');
Ts = PRM.Ts;

% ---------------- library blocks (found by name, robust to library layout) ----------------
L.gui  = libblock('powergui');
L.cvs  = libblock('Controlled Voltage Source');
L.ccs  = libblock('Controlled Current Source');
L.rlc  = libblock('Three-Phase Series RLC Branch');
L.vim  = libblock('Three-Phase V-I Measurement');
L.gnd  = libblock('Ground');

% ---------------- solver ----------------
add_block(L.gui, [mdl '/powergui'], 'Position', [20 20 90 60]);
setp([mdl '/powergui'], 'SimulationMode', 'Discrete');
setp([mdl '/powergui'], 'SampleTime', num2str(Ts, 16));
set_param(mdl, 'Solver', 'FixedStepDiscrete', 'FixedStep', num2str(Ts, 16), ...
          'StopTime', num2str(PRM.Tw + PRM.T_ep), 'SaveOutput', 'off', 'SaveTime', 'off', ...
          'ReturnWorkspaceOutputs', 'on');

% ---------------- three-phase source sets (VSG, diesel) and load injection ----------------
srcV = add_source(mdl, L, 'VSG', L.cvs, [200 100]);
srcD = add_source(mdl, L, 'Diesel', L.cvs, [200 500]);
srcL = add_source(mdl, L, 'Load', L.ccs, [1100 300]);

% coupling impedances
add_block(L.rlc, [mdl '/Z_vsg'], 'Position', [420 110 470 210]);
setrl([mdl '/Z_vsg'], PRM.R_v_ohm, PRM.L_v_H);
add_block(L.rlc, [mdl '/Z_diesel'], 'Position', [420 510 470 610]);
setrl([mdl '/Z_diesel'], PRM.R_d_ohm, PRM.L_d_H);
% shunt resistance at the bus (also avoids an all-inductive node with a current source)
add_block(L.rlc, [mdl '/R_shunt'], 'Position', [760 330 810 430]);
setp([mdl '/R_shunt'], 'BranchType', 'R');
setp([mdl '/R_shunt'], 'Resistance', num2str(PRM.R_sh_ohm, 16));
% measurements
add_block(L.vim, [mdl '/VI_vsg'], 'Position', [540 110 600 210]);
add_block(L.vim, [mdl '/VI_diesel'], 'Position', [540 510 600 610]);
add_block(L.vim, [mdl '/VI_load'], 'Position', [900 310 960 410]);
add_block(L.gnd, [mdl '/G_shunt'], 'Position', [860 450 890 480]);
for b = {'VI_vsg', 'VI_diesel', 'VI_load'}          % outputs in volts and amperes
    soft([mdl '/' b{1}], 'VoltageMeasurement', 'phase-to-ground');
    soft([mdl '/' b{1}], 'CurrentMeasurement', 'yes');
    soft([mdl '/' b{1}], 'SetLabelV', 'off');  soft([mdl '/' b{1}], 'SetLabelI', 'off');
    soft([mdl '/' b{1}], 'Vpu', 'off');  soft([mdl '/' b{1}], 'Ipu', 'off');
end

% electrical connections
for k = 1:3
    pconn(mdl, srcV.plus(k), port([mdl '/Z_vsg'], 'L', k));
    pconn(mdl, port([mdl '/Z_vsg'], 'R', k), port([mdl '/VI_vsg'], 'L', k));
    pconn(mdl, srcD.plus(k), port([mdl '/Z_diesel'], 'L', k));
    pconn(mdl, port([mdl '/Z_diesel'], 'R', k), port([mdl '/VI_diesel'], 'L', k));
    % bus node: VSG side, diesel side, shunt, load measurement
    pconn(mdl, port([mdl '/VI_vsg'], 'R', k), port([mdl '/R_shunt'], 'L', k));
    pconn(mdl, port([mdl '/VI_diesel'], 'R', k), port([mdl '/R_shunt'], 'L', k));
    pconn(mdl, port([mdl '/R_shunt'], 'L', k), port([mdl '/VI_load'], 'L', k));
    pconn(mdl, port([mdl '/VI_load'], 'R', k), srcL.plus(k));
    pconn(mdl, port([mdl '/R_shunt'], 'R', k), port([mdl '/G_shunt'], 'L', 1));
end

% ---------------- controller ----------------
add_block('simulink/Signal Routing/Mux', [mdl '/MeasMux'], 'Inputs', '4', 'Position', [700 680 710 780]);
add_block('simulink/Discrete/Unit Delay', [mdl '/MeasDelay'], 'SampleTime', num2str(Ts, 16), ...
          'InitialCondition', 'zeros(12,1)', 'Position', [760 710 800 750]);
add_block('simulink/User-Defined Functions/MATLAB Function', [mdl '/Controller'], 'Position', [860 690 1000 790]);
set_mlfb([mdl '/Controller'], ...
    ['function [vv, vd, il, mon] = ctrl(meas, PRM)' newline ...
     '%#codegen' newline ...
     '[vv, vd, il, mon] = vsgrl_emt_ctrl(meas, PRM);' newline ...
     'end' newline]);
add_line(mdl, 'VI_load/1', 'MeasMux/1', 'autorouting', 'on');      % bus voltage (load side = bus)
add_line(mdl, 'VI_vsg/2', 'MeasMux/2', 'autorouting', 'on');
add_line(mdl, 'VI_diesel/2', 'MeasMux/3', 'autorouting', 'on');
add_line(mdl, 'VI_load/2', 'MeasMux/4', 'autorouting', 'on');
add_line(mdl, 'MeasMux/1', 'MeasDelay/1', 'autorouting', 'on');
add_line(mdl, 'MeasDelay/1', 'Controller/1', 'autorouting', 'on');
add_line(mdl, 'Controller/1', [srcV.name '_demux/1'], 'autorouting', 'on');
add_line(mdl, 'Controller/2', [srcD.name '_demux/1'], 'autorouting', 'on');
add_line(mdl, 'Controller/3', [srcL.name '_demux/1'], 'autorouting', 'on');
add_block('simulink/Sinks/To Workspace', [mdl '/Log'], 'VariableName', 'emt_mon', 'SaveFormat', 'Array', ...
          'Decimation', num2str(round(0.01 / Ts)), 'Position', [1100 760 1180 790]);
add_line(mdl, 'Controller/4', 'Log/1', 'autorouting', 'on');

save_system(mdl, file);
fprintf('Built %s\n', file);
end

% =====================================================================================
function s = add_source(mdl, L, name, lib, xy)
% three single-phase controlled sources, star-connected to ground, driven through a Demux
x = xy(1);  y = xy(2);
s.name = name;
add_block('simulink/Signal Routing/Demux', [mdl '/' name '_demux'], 'Outputs', '3', ...
          'Position', [x - 120, y, x - 110, y + 120]);
s.plus = zeros(1, 3);
for k = 1:3
    b = sprintf('%s/%s_%c', mdl, name, 'a' + k - 1);
    add_block(lib, b, 'Position', [x, y + (k - 1) * 45, x + 40, y + (k - 1) * 45 + 35]);
    g = sprintf('%s/%s_gnd_%c', mdl, name, 'a' + k - 1);
    add_block(L.gnd, g, 'Position', [x + 5, y + (k - 1) * 45 + 160, x + 35, y + (k - 1) * 45 + 185]);
    add_line(mdl, sprintf('%s_demux/%d', name, k), sprintf('%s_%c/1', name, 'a' + k - 1), 'autorouting', 'on');
    pc = cons(b);                                  % [+ terminal, - terminal]
    pconn(mdl, pc(2), port(g, 'L', 1));
    s.plus(k) = pc(1);
end
end

function pc = cons(b)
% physical ports of a two-terminal SPS source, ordered [+, -]
ph = get_param(b, 'PortHandles');
pc = [ph.LConn, ph.RConn];
if numel(pc) ~= 2
    error('Unexpected port layout of %s (%d physical ports).', b, numel(pc));
end
end

function h = port(b, side, k)
ph = get_param(b, 'PortHandles');
if side == 'L', h = ph.LConn(k); else, h = ph.RConn(k); end
end

function pconn(mdl, h1, h2)
try
    add_line(mdl, h1, h2, 'autorouting', 'on');
catch e
    error('Could not connect %s to %s: %s', getfullname(get_param(h1, 'Parent')), ...
          getfullname(get_param(h2, 'Parent')), e.message);
end
end

function setrl(b, R, Lh)
setp(b, 'BranchType', 'RL');
setp(b, 'Resistance', num2str(R, 16));
setp(b, 'Inductance', num2str(Lh, 16));
end

function soft(b, name, val)
% set a parameter if the block has it (names differ slightly between releases)
dp = get_param(b, 'DialogParameters');
if isfield(dp, name)
    try, set_param(b, name, val); catch, end
end
end

function setp(b, name, val)
try
    set_param(b, name, val);
catch e
    dp = get_param(b, 'DialogParameters');
    error('Could not set "%s" on %s (%s).\nAvailable parameters: %s', name, b, e.message, ...
          strjoin(fieldnames(dp)', ', '));
end
end

function path = libblock(name)
% find a block in the Specialized Power Systems library by its (display) name
persistent all names
if isempty(all)
    all = find_system('powerlib', 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Type', 'Block');
    names = regexprep(get_param(all, 'Name'), '\s+', ' ');
end
hit = all(strcmpi(names, name));
if isempty(hit)
    error('Block "%s" not found in powerlib (Simscape Electrical / Specialized Power Systems).', name);
end
[~, i] = min(cellfun(@(p) sum(p == '/'), hit));   % library-level block, not a sub-block
path = hit{i};
end

function set_mlfb(blk, code)
% set the code of a MATLAB Function block and make PRM a (non-tunable) parameter
rt = sfroot;
ch = rt.find('-isa', 'Stateflow.EMChart', 'Path', blk);
ch.Script = code;
d = ch.find('-isa', 'Stateflow.Data', 'Name', 'PRM');
if isempty(d)
    d = Stateflow.Data(ch);  d.Name = 'PRM';
end
d.Scope = 'Parameter';
d.Tunable = true;                                % new scenarios without recompiling
end
