function P = vsgrl_wind_power(C, v, rho)
%VSGRL_WIND_POWER  Generic pitch-regulated turbine curve with IEC density correction (MW).
v = v * (rho / 1.225)^(1/3);
if v < C.w_ci || v >= C.w_co
    P = 0;
elseif v >= C.w_vr
    P = C.w_rated;
else
    P = C.w_rated * (v^3 - C.w_ci^3) / (C.w_vr^3 - C.w_ci^3);
end
end
