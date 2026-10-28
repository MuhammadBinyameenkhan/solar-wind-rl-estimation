%DIAGNOSE_SIMSCAPE  Report the Simscape Electrical blocks and parameter names this MATLAB provides.
%   Run from matlab/simscape and send the printed text if build_vsgrl_simscape fails.
fprintf('MATLAB %s\n', version);
v = ver;  n = {v.Name};
for t = {'Simulink', 'Simscape', 'Simscape Electrical'}
    fprintf('  %-22s %s\n', t{1}, ternary_str(any(strcmp(n, t{1}))));
end
try
    load_system('powerlib');  fprintf('powerlib loaded\n');
catch e
    fprintf('powerlib NOT loaded: %s\n', e.message);  return
end
blocks = {'powerlib/powergui', 'powerlib/Electrical Sources/Controlled Voltage Source', ...
          'powerlib/Electrical Sources/Controlled Current Source', 'powerlib/Elements/Three-Phase Series RLC Branch', ...
          'powerlib/Measurements/Three-Phase V-I Measurement', 'powerlib/Elements/Ground'};
for i = 1:numel(blocks)
    try
        dp = fieldnames(get_param(blocks{i}, 'DialogParameters'));
        ph = get_param(blocks{i}, 'PortHandles');
        fprintf('OK   %s\n     ports: in %d out %d L %d R %d\n     params: %s\n', blocks{i}, numel(ph.Inport), ...
                numel(ph.Outport), numel(ph.LConn), numel(ph.RConn), strjoin(dp', ', '));
    catch e
        fprintf('MISSING %s (%s)\n', blocks{i}, e.message);
    end
end
fprintf('Top-level powerlib entries: %s\n', strjoin(find_system('powerlib', 'SearchDepth', 1, 'Type', 'Block')', ' | '));
for lib = {'sps_lib', 'spsLib', 'powerlib_extras'}
    try
        load_system(lib{1});
        g = find_system(lib{1}, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', 'powergui');
        fprintf('%s loaded; powergui: %s\n', lib{1}, strjoin(g', ' | '));
    catch
        fprintf('%s: not available\n', lib{1});
    end
end
fprintf('vsgrl_emt_ctrl.m on path: %s\n', which('vsgrl_emt_ctrl'));

function s = ternary_str(c)
if c, s = 'installed'; else, s = 'NOT installed'; end
end
