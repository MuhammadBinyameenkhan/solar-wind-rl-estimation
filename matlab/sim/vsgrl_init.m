function C = vsgrl_init(p)
%VSGRL_INIT  Derived model constants from the exported parameter struct (vsgrl_params.mat).
%   Mirrors Microgrid.__init__ and VSGEnv.__init__ in the Python code (vsgrl/).
C.f0 = p.system_f_nominal_hz;   C.w0 = 2*pi*C.f0;   C.Sb = p.system_s_base_mva;
C.dt = p.env_sim_dt_s;
% diesel synchronous generator
C.Pd_rat = p.system_diesel_rated_mw / C.Sb;
C.inv_R = (1/p.system_diesel_droop) * C.Pd_rat;
C.Tg = p.system_diesel_governor_time_s;   C.Te = p.system_diesel_engine_time_s;
C.Pd_min = p.system_diesel_min_load_frac * C.Pd_rat;
C.Pd_disp_max = p.system_diesel_max_dispatch_frac * C.Pd_rat;
C.ramp = p.system_diesel_ramp_pu_per_s * C.Pd_rat;
C.Ki = p.system_diesel_secondary_ki;   C.Ki_b = p.system_bess_secondary_ki;
C.H_d = p.system_diesel_inertia_h_s * p.system_diesel_rated_mw / C.Sb;
C.D_d = p.system_diesel_damping_pu * C.Pd_rat;
C.Kd = p.system_diesel_sync_coeff_pu;
% BESS
C.Pb_max = p.system_bess_power_mw / C.Sb;   C.Eb = p.system_bess_energy_mwh;
C.soc_min = p.system_bess_soc_min;   C.soc_max = p.system_bess_soc_max;   C.soc_taper = p.system_bess_soc_taper;
C.eta_c = p.system_bess_eta_charge;   C.eta_d = p.system_bess_eta_discharge;
% PV, wind, load
C.deload = p.system_pv_deload_fraction;   C.Tpv = max(p.system_pv_response_time_s, C.dt);
C.TI = p.system_wind_turbulence_intensity;   C.Trot = max(p.system_wind_rotor_smoothing_s, C.dt);
C.w_rated = p.system_wind_rated_mw;   C.w_ci = p.system_wind_cut_in_ms;
C.w_vr = p.system_wind_rated_speed_ms;   C.w_co = p.system_wind_cut_out_ms;
C.DL = p.system_load_damping_pu;   C.load_noise = p.system_load_noise_frac;
% VSG
C.Ks = p.system_vsg_sync_coeff_pu;   C.Tf = max(p.system_vsg_measurement_filter_s, C.dt);
C.h_min = p.system_vsg_h_min_s;   C.h_max = p.system_vsg_h_max_s;
C.d_min = p.system_vsg_d_min_pu;   C.d_max = p.system_vsg_d_max_pu;
% EMS
C.ems_on = p.system_ems_enabled > 0;
C.ems_target = p.system_ems_diesel_target_frac;   C.ems_max = p.system_ems_max_dispatch_frac;
% grid code, reward, episode
C.f_lim = p.system_grid_code_f_dev_limit_hz / C.f0;   C.r_lim = p.system_grid_code_rocof_limit_hz_s / C.f0;
C.f_target = p.system_grid_code_f_target_hz;   C.rocof_limit_hz = p.system_grid_code_rocof_limit_hz_s;
C.rocof_window_s = p.system_grid_code_rocof_window_s;
C.f_band = p.env_reward_f_band_hz / C.f0;   C.r_band = p.env_reward_rocof_band_hz_s / C.f0;
C.w = struct('freq', p.env_reward_w_freq, 'inband', p.env_reward_w_freq_inband, ...
             'rocof', p.env_reward_w_rocof, 'bess', p.env_reward_w_bess, 'fast', p.env_reward_w_fast, ...
             'sat', p.env_reward_w_sat, 'viol', p.env_reward_w_violation, 'collapse', p.env_reward_collapse_penalty);
C.agent_dt = p.env_agent_dt_s;   C.n_sub = round(C.agent_dt / C.dt);
C.max_steps = round(p.env_episode_s / C.agent_dt);
C.param_tau = p.env_param_filter_s;   C.term_hz = p.env_terminate_dev_hz;
C.trace_every = 5;
end
