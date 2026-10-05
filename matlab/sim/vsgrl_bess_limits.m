function [dis, ch] = vsgrl_bess_limits(C, soc)
%VSGRL_BESS_LIMITS  SoC-dependent discharge / charge power limits (S_base pu), linear taper.
dis = C.Pb_max * min(max((soc - C.soc_min) / C.soc_taper, 0), 1);
ch  = C.Pb_max * min(max((C.soc_max - soc) / C.soc_taper, 0), 1);
end
