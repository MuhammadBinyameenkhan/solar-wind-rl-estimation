function h = vsgrl_headroom(C, S, direction)
%VSGRL_HEADROOM  Fast reserve the VSG can deliver now (S_base pu). direction: 'up' | 'down' | 'auto'
%   'auto' = upward while f <= nominal, downward during an over-frequency event.
if strcmp(direction, 'auto')
    if S.f_meas <= 0, direction = 'up'; else, direction = 'down'; end
end
[dis, ch] = vsgrl_bess_limits(C, S.soc);
if strcmp(direction, 'up')
    h = max(dis - S.pb0, 0) + S.h_pv;
else
    h = max(ch + S.pb0, 0) + S.pv_base;
end
end
