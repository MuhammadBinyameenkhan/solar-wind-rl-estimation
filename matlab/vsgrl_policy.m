function [H, D, alpha, a] = vsgrl_policy(obs, pol, bounds)
%VSGRL_POLICY  Forward pass of the exported RL actor (TD3/DDPG) + action mapping.
%   obs    : 16x1 normalised observation, same order as pol.obs_names
%            (build it with vsgrl_build_obs.m)
%   pol    : struct loaded from vsgrl_policy_<algo>_seed<k>.mat
%   bounds : [H_ub, D_ub] from vsgrl_headroom_bounds.m (feasibility projection);
%            omit to use the static ranges.
%   Returns virtual inertia H [s], damping D [pu on S_base], PV share alpha [-],
%   and the raw action a in [-1,1].
%
%   Use inside a MATLAB Function block sampled at pol.agent_dt_s (50 ms, ZOH).
%#codegen
x = obs(:);
n = round(pol.n_layers);
for i = 1:n
    W = pol.(sprintf('W%d', i));
    b = pol.(sprintf('b%d', i));
    x = W * x + b;
    if i < n
        x = max(x, 0);            % ReLU
    else
        x = tanh(x);              % bounded action
    end
end
a = min(max(x, -1), 1);
if nargin < 3 || isempty(bounds)
    bounds = [pol.h_max, pol.d_max];
end
if isfield(pol, 'residual') && pol.residual
    % residual mode: a = 0 -> nominal VSG, a = +-1 -> (projected) bounds
    H = resid(a(1), pol.nominal_h, pol.h_min, bounds(1));
    D = resid(a(2), pol.nominal_d, pol.d_min, bounds(2));
    if numel(a) >= 3
        alpha = resid(a(3), pol.nominal_alpha, pol.alpha_min, pol.alpha_max);
    else
        alpha = pol.nominal_alpha;
    end
else
    H = pol.h_min + 0.5 * (a(1) + 1) * (bounds(1) - pol.h_min);
    D = pol.d_min + 0.5 * (a(2) + 1) * (bounds(2) - pol.d_min);
    if numel(a) >= 3
        alpha = pol.alpha_min + 0.5 * (a(3) + 1) * (pol.alpha_max - pol.alpha_min);
    else
        alpha = 0.3;
    end
end
end

function y = resid(a, nominal, lo, hi)
nominal = min(max(nominal, lo), hi);
if a >= 0
    y = nominal + a * (hi - nominal);
else
    y = nominal + a * (nominal - lo);
end
end
