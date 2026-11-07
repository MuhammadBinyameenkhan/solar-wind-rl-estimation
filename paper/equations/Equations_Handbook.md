---
title: Equation Handbook
subtitle: Thesis proposal and IREA manuscript (M. B. Khan, SUT)
---

This handbook lists every equation of the thesis proposal (Chapter 3) and of the IREA manuscript, in proper mathematical form, with its LaTeX source and an explanation of each symbol. The equations themselves are unchanged; only the notation is typeset properly.

## How to put these equations into Word

**Method 1, any Word version (easiest).** Every equation in this file is a real Word equation. Click it, select it (Ctrl+A inside the equation box selects the whole equation), copy, and paste it into the proposal or the IREA manuscript. Then type the number, for example (3.1), at the right with a tab.

**Method 2, Word for Microsoft 365 or Word 2021 (LaTeX input).** Click where the equation should go and press **Alt + =**. On the **Equation** tab choose **LaTeX** in the Conversions group, paste the LaTeX line shown under the equation, and press **Convert → Professional** (or Ctrl + =). If an older Word shows `\mathrm` or `\text` literally, delete those commands and keep the braces' contents.

**Method 3, LaTeX documents.** The file `equations.tex` contains every equation numbered as in the proposal. Paste it into Overleaf or compile it with pdflatex.

**Numbering in Word.** A neat way is a 3-column table without borders: empty narrow cell, equation centred, number right-aligned. Or type the equation, then `#(3.1)` at its end inside the equation box and press Enter: Word 365 places the number at the right automatically.

**Equation numbers.** Proposal numbers are (3.1)–(3.26); the IREA manuscript uses (1)–(10). The cross-reference table below maps them.


## Cross-reference: proposal and IREA numbers

| Proposal | IREA | Equation |
|---|---|---|
| (3.1) | – | PV cell temperature |
| (3.2) | – | PV output power |
| (3.3) | – | Wind turbine mechanical power (Study 1) |
| (3.4) | – | Power coefficient of the turbine |
| (3.5) | – | Wind power curve with density correction (Study 2) |
| (3.6) | – | VSG power injection (Study 1) |
| (3.7) | – | Closed-loop swing equation (Study 1) |
| (3.8) | – | Power imbalance and BESS droop (Study 1) |
| (3.9) | – | BESS scheduling and voltage-dependent load (Study 1) |
| (3.10) | – | Reactive-power droop with apparent-power limit (Study 1) |
| (3.11) | – | PLL frequency measurement (Study 1) |
| (3.12) | (1) | VSG electrical power and net imbalance |
| (3.13) | (2) | Bus frequency |
| (3.14) | (3) | Diesel generator swing equation |
| (3.15) | (4) | VSG virtual-rotor equations |
| (3.16) | (5) | VSG power band |
| (3.16a) | – | PV share of the support |
| (3.17) | – | Summed headroom requirement (Study 1) |
| – | (7) | Summed headroom requirement (Study 2 notation) |
| (3.18) | – | Available headroom (Study 1) |
| (3.19) | (9) | Proportional derating |
| (3.20) | (6) | Direction-aware headroom (Study 2) |
| (3.21) | (8) | Time-separated (max) headroom requirement |
| (3.22) | – | Residual action mapping (Study 2) |
| (3.23) | (10) | Interval cost (Study 2) |
| (3.24) | – | TD3 critic target |
| (3.25) | – | Frequency error integrals |
| (3.26) | – | Oracle gain |

## Part A. Renewable sources and Study 1 microgrid (proposal Sections 3.3–3.5.1)

### PV cell temperature

*Proposal (3.1)*

$$ T_{\mathrm{cell}} = T_{\mathrm{amb}} + k_{\mathrm{NOCT}}\,G $$

LaTeX for Word:

```
T_{\mathrm{cell}} = T_{\mathrm{amb}} + k_{\mathrm{NOCT}}\,G
```

The cell runs hotter than the air in proportion to the irradiance falling on it. Study 1 uses k_NOCT = 0.030 °C·m²/W; Study 2 uses k_NOCT = (NOCT − 20)/800 = 0.031 °C·m²/W for NOCT = 45 °C.

Where:

- $T_{\mathrm{cell}}$: cell temperature (°C)
- $T_{\mathrm{amb}}$: ambient air temperature (°C)
- $k_{\mathrm{NOCT}}$: temperature-rise coefficient (°C·m²/W)
- $G$: plane irradiance (W/m²)

### PV output power

*Proposal (3.2)*

$$ P_{\mathrm{pv}} = \eta_{\mathrm{deg}}\,P_{\mathrm{pv,rated}}\,\frac{G}{G_{\mathrm{ref}}}\left[1 - C_T\left(T_{\mathrm{cell}} - T_{\mathrm{ref}}\right)\right], \qquad 0 \le P_{\mathrm{pv}} \le P_{\mathrm{pv,rated}} $$

LaTeX for Word:

```
P_{\mathrm{pv}} = \eta_{\mathrm{deg}}\,P_{\mathrm{pv,rated}}\,\frac{G}{G_{\mathrm{ref}}}\left[1 - C_T\left(T_{\mathrm{cell}} - T_{\mathrm{ref}}\right)\right], \qquad 0 \le P_{\mathrm{pv}} \le P_{\mathrm{pv,rated}}
```

PV power rises linearly with irradiance and falls by C_T per degree of cell temperature above 25 °C (Skoplaki and Palyvos, 2009). The output is limited to the plant rating. In Study 2 a system derating of 0.90 replaces η_deg and C_T = 0.004 °C⁻¹.

Where:

- $\eta_{\mathrm{deg}}$: degradation factor (0.995 in Study 1)
- $P_{\mathrm{pv,rated}}$: rated PV power
- $G_{\mathrm{ref}}$: reference irradiance, 1000 W/m²
- $C_T$: temperature coefficient (0.0045 °C⁻¹ in Study 1)
- $T_{\mathrm{ref}}$: reference temperature, 25 °C

### Wind turbine mechanical power (Study 1)

*Proposal (3.3)*

$$ P_m = \frac{1}{2}\,\rho\,\pi R^{2}\,C_p(\lambda,\beta)\,v_w^{3} $$

LaTeX for Word:

```
P_m = \frac{1}{2}\,\rho\,\pi R^{2}\,C_p(\lambda,\beta)\,v_w^{3}
```

Power extracted by the rotor from the wind passing through the swept area πR². With ρ = 1.225 kg/m³ and R = 18.9 m the turbine gives 500 kW at 11.5 m/s.

Where:

- $\rho$: air density (kg/m³)
- $R$: rotor radius (m)
- $C_p$: power coefficient
- $\lambda$: tip-speed ratio, $\lambda = \omega_r R / v_w$
- $\beta$: pitch angle (degrees)
- $v_w$: wind speed (m/s)

### Power coefficient of the turbine

*Proposal (3.4)*

$$ C_p = 0.5176\left(\frac{116}{\lambda_i} - 0.4\,\beta - 5\right)e^{-21/\lambda_i} + 0.0068\,\lambda, \qquad \frac{1}{\lambda_i} = \frac{1}{\lambda + 0.08\,\beta} - \frac{0.035}{\beta^{3} + 1} $$

LaTeX for Word:

```
C_p = 0.5176\left(\frac{116}{\lambda_i} - 0.4\,\beta - 5\right)e^{-21/\lambda_i} + 0.0068\,\lambda, \qquad \frac{1}{\lambda_i} = \frac{1}{\lambda + 0.08\,\beta} - \frac{0.035}{\beta^{3} + 1}
```

Standard empirical C_p(λ, β) curve (Slootweg et al., 2003). Its maximum at β = 0 gives the optimal tip-speed ratio of 8.10 used by the optimal-torque controller.

Where:

- $\lambda_i$: intermediate tip-speed ratio

### Wind power curve with density correction (Study 2)

*Proposal (3.5)*

$$ P_w = \begin{cases} P_r\,\dfrac{v'^{3} - v_{\mathrm{ci}}^{3}}{v_r^{3} - v_{\mathrm{ci}}^{3}}, & v_{\mathrm{ci}} \le v' < v_r \\ P_r, & v_r \le v' < v_{\mathrm{co}} \\ 0, & \text{otherwise} \end{cases} \qquad v' = v\left(\frac{\rho}{1.225}\right)^{1/3} $$

LaTeX for Word:

```
P_w = \begin{cases} P_r\,\dfrac{v'^{3} - v_{\mathrm{ci}}^{3}}{v_r^{3} - v_{\mathrm{ci}}^{3}}, & v_{\mathrm{ci}} \le v' < v_r \\ P_r, & v_r \le v' < v_{\mathrm{co}} \\ 0, & \text{otherwise} \end{cases} \qquad v' = v\left(\frac{\rho}{1.225}\right)^{1/3}
```

IEC class III pitch-regulated power curve for hourly ERA5 wind. The wind speed is first corrected to standard air density (IEC 61400-12-1). The zero branch (below cut-in or above cut-out) is implied in the documents and written out here.

Where:

- $P_r$: rated power, 1.0 MW
- $v_{\mathrm{ci}},\ v_r,\ v_{\mathrm{co}}$: cut-in 2.5 m/s, rated 10 m/s, cut-out 25 m/s
- $v'$: density-corrected wind speed at 100 m hub height

### VSG power injection (Study 1)

*Proposal (3.6)*

$$ p_{\mathrm{vsg}} = -2\,J_{\mathrm{eff}}\,\frac{d\Delta\omega}{dt} - D_{\mathrm{eff}}\,\Delta\omega_m $$

LaTeX for Word:

```
p_{\mathrm{vsg}} = -2\,J_{\mathrm{eff}}\,\frac{d\Delta\omega}{dt} - D_{\mathrm{eff}}\,\Delta\omega_m
```

The VSG injects an inertial power proportional to the rate of change of frequency and a damping power proportional to the PLL-measured frequency deviation. All quantities are per unit on S_base = 2500 kVA, with Δω = (f − f₀)/f₀ and f₀ = 50 Hz.

Where:

- $p_{\mathrm{vsg}}$: VSG active power (pu)
- $J_{\mathrm{eff}}$: effective virtual inertia after derating (s)
- $D_{\mathrm{eff}}$: effective virtual damping after derating (pu)
- $\Delta\omega_m$: measured frequency deviation (pu)

### Closed-loop swing equation (Study 1)

*Proposal (3.7)*

$$ 2\left(H_{\mathrm{sys}} + J_{\mathrm{eff}}\right)\frac{d\Delta\omega}{dt} = \Delta P_{\mathrm{ext}} - D_{\mathrm{eff}}\,\Delta\omega_m $$

LaTeX for Word:

```
2\left(H_{\mathrm{sys}} + J_{\mathrm{eff}}\right)\frac{d\Delta\omega}{dt} = \Delta P_{\mathrm{ext}} - D_{\mathrm{eff}}\,\Delta\omega_m
```

Substituting (3.6) into the system swing equation: the virtual inertia adds to the small residual inertia of the converter-only system (Kundur, 1994).

Where:

- $H_{\mathrm{sys}}$: residual system inertia, 0.5 s
- $\Delta P_{\mathrm{ext}}$: external power imbalance (pu)

### Power imbalance and BESS droop (Study 1)

*Proposal (3.8)*

$$ \Delta P_{\mathrm{ext}} = \frac{P_{\mathrm{pv}} + P_w + P_{\mathrm{sch}} - P_{\mathrm{load}}}{S_{\mathrm{base}}} + p_{\mathrm{dr}}, \qquad T_{\mathrm{dr}}\,\frac{dp_{\mathrm{dr}}}{dt} = -\frac{1}{R}\,\Delta\omega_m - p_{\mathrm{dr}} $$

LaTeX for Word:

```
\Delta P_{\mathrm{ext}} = \frac{P_{\mathrm{pv}} + P_w + P_{\mathrm{sch}} - P_{\mathrm{load}}}{S_{\mathrm{base}}} + p_{\mathrm{dr}}, \qquad T_{\mathrm{dr}}\,\frac{dp_{\mathrm{dr}}}{dt} = -\frac{1}{R}\,\Delta\omega_m - p_{\mathrm{dr}}
```

The imbalance is generation minus load plus the primary droop response of the BESS, which follows the measured deviation through a first-order lag.

Where:

- $P_{\mathrm{sch}}$: scheduled BESS power
- $p_{\mathrm{dr}}$: droop power (pu)
- $1/R$: droop gain, 10 pu
- $T_{\mathrm{dr}}$: droop time constant, 0.5 s

### BESS scheduling and voltage-dependent load (Study 1)

*Proposal (3.9)*

$$ \tau_{\mathrm{sch}}\,\frac{dP_{\mathrm{gen},f}}{dt} = P_{\mathrm{pv}} + P_w - P_{\mathrm{gen},f}, \qquad P_{\mathrm{sch}} = P_{\mathrm{load,nom}}\left(\frac{V}{V_{\mathrm{nom}}}\right)^{k_p} - P_{\mathrm{gen},f} $$

LaTeX for Word:

```
\tau_{\mathrm{sch}}\,\frac{dP_{\mathrm{gen},f}}{dt} = P_{\mathrm{pv}} + P_w - P_{\mathrm{gen},f}, \qquad P_{\mathrm{sch}} = P_{\mathrm{load,nom}}\left(\frac{V}{V_{\mathrm{nom}}}\right)^{k_p} - P_{\mathrm{gen},f}
```

The BESS set-point follows a filtered renewable estimate, so only the fast part of the renewable fluctuation reaches the network. The load depends on voltage through the exponent k_p.

Where:

- $\tau_{\mathrm{sch}}$: scheduling filter time constant, 1 s
- $P_{\mathrm{gen},f}$: filtered renewable power
- $k_p$: load voltage exponent

### Reactive-power droop with apparent-power limit (Study 1)

*Proposal (3.10)*

$$ q_{\mathrm{vsg}} = K_q\left(V_{\mathrm{nom}} - V\right), \qquad \left|q_{\mathrm{vsg}}\right| \le \frac{\sqrt{S_{\mathrm{rated}}^{2} - P_{\mathrm{bess}}^{2}}}{S_{\mathrm{base}}} $$

LaTeX for Word:

```
q_{\mathrm{vsg}} = K_q\left(V_{\mathrm{nom}} - V\right), \qquad \left|q_{\mathrm{vsg}}\right| \le \frac{\sqrt{S_{\mathrm{rated}}^{2} - P_{\mathrm{bess}}^{2}}}{S_{\mathrm{base}}}
```

Reactive support is a voltage droop limited by what is left of the converter rating after active power, so frequency and voltage support compete for the same capacity.

Where:

- $K_q$: voltage droop gain (2–20 pu, scheduled by the agent)
- $S_{\mathrm{rated}}$: converter rating

### PLL frequency measurement (Study 1)

*Proposal (3.11)*

$$ \tau_{\mathrm{pll}}\,\frac{df_m}{dt} = f + n - f_m, \qquad n \sim \mathcal{N}\!\left(0,\ \sigma_{\mathrm{pll}}^{2}\right) $$

LaTeX for Word:

```
\tau_{\mathrm{pll}}\,\frac{df_m}{dt} = f + n - f_m, \qquad n \sim \mathcal{N}\!\left(0,\ \sigma_{\mathrm{pll}}^{2}\right)
```

The controller sees the frequency through a first-order lag with Gaussian measurement noise, τ_pll = 20 ms and σ_pll = 8 mHz.

Where:

- $f_m$: measured frequency
- $n$: measurement noise

## Part B. Study 2 hybrid diesel–VSG microgrid (proposal Section 3.5.2, IREA Section III.A)

### VSG electrical power and net imbalance

*Proposal (3.12) · IREA (1)*

$$ P_v = \frac{K_s\left(K_d\,\delta + \Delta P_{\mathrm{net}}\right)}{K_d + K_s}, \qquad \Delta P_{\mathrm{net}} = \Delta P_L - \Delta P_w + D_L\,P_{L0}\,\Delta\omega_b $$

LaTeX for Word:

```
P_v = \frac{K_s\left(K_d\,\delta + \Delta P_{\mathrm{net}}\right)}{K_d + K_s}, \qquad \Delta P_{\mathrm{net}} = \Delta P_L - \Delta P_w + D_L\,P_{L0}\,\Delta\omega_b
```

The network shares the net imbalance between the diesel generator and the VSG in proportion to their synchronising coefficients. At the instant of a step (δ = 0) the VSG takes K_s/(K_d + K_s) = 2.0/2.8 ≈ 71 % of it, whatever J_v and D_v are. The diesel takes the rest, ΔP_e,d = ΔP_net − P_v (from the model code; not printed in the documents).

Where:

- $K_d,\ K_s$: synchronising coefficients of the diesel (0.8 pu) and the VSG (2.0 pu)
- $\delta$: angle of the virtual rotor relative to the diesel rotor (rad)
- $\Delta P_L$: load change
- $\Delta P_w$: wind power change
- $D_L$: load damping, 1 pu
- $P_{L0}$: initial load

### Bus frequency

*Proposal (3.13) · IREA (2)*

$$ \Delta\omega_b = \frac{K_d\,\Delta\omega_d + K_s\,\Delta\omega_v}{K_d + K_s} $$

LaTeX for Word:

```
\Delta\omega_b = \frac{K_d\,\Delta\omega_d + K_s\,\Delta\omega_v}{K_d + K_s}
```

The load-bus frequency is the coefficient-weighted mean of the two rotor speeds.

Where:

- $\Delta\omega_d,\ \Delta\omega_v$: speed deviations of the diesel rotor and the virtual rotor (pu)

### Diesel generator swing equation

*Proposal (3.14) · IREA (3)*

$$ 2H_d\,\frac{d\Delta\omega_d}{dt} = \Delta P_m - \Delta P_{e,d} - D_d\left(\Delta\omega_d - \Delta\omega_b\right) $$

LaTeX for Word:

```
2H_d\,\frac{d\Delta\omega_d}{dt} = \Delta P_m - \Delta P_{e,d} - D_d\left(\Delta\omega_d - \Delta\omega_b\right)
```

Physical inertia of the diesel unit. ΔP_m comes from a 5 % droop governor with governor and engine lags (0.2 s, 0.5 s) and automatic generation control.

Where:

- $H_d$: diesel inertia constant, 2 s
- $\Delta P_m$: mechanical power change
- $\Delta P_{e,d}$: diesel electrical power change, $\Delta P_{\mathrm{net}} - P_v$
- $D_d$: diesel damping

### VSG virtual-rotor equations

*Proposal (3.15) · IREA (4)*

$$ 2J_v\,\frac{d\Delta\omega_v}{dt} = P_{\mathrm{set}} - P_v - D_v\,\Delta\omega_v, \qquad \frac{d\delta}{dt} = \omega_0\left(\Delta\omega_v - \Delta\omega_d\right) $$

LaTeX for Word:

```
2J_v\,\frac{d\Delta\omega_v}{dt} = P_{\mathrm{set}} - P_v - D_v\,\Delta\omega_v, \qquad \frac{d\delta}{dt} = \omega_0\left(\Delta\omega_v - \Delta\omega_d\right)
```

The virtual rotor of the grid-forming BESS converter. J_v and D_v are the parameters the agent schedules; P_set is moved by an integral BESS secondary control.

Where:

- $J_v$: virtual inertia (0.2–8 s)
- $D_v$: virtual damping (0–50 pu)
- $P_{\mathrm{set}}$: VSG power set-point
- $\omega_0$: nominal angular frequency, $2\pi \cdot 50$ rad/s

### VSG power band

*Proposal (3.16) · IREA (5)*

$$ -\left(P_{\mathrm{ch,max}}(\mathrm{SoC}) + P_{b0}\right) + P_{\mathrm{pv},s} \;\le\; P_v \;\le\; P_{\mathrm{dis,max}}(\mathrm{SoC}) - P_{b0} + P_{\mathrm{pv},s} $$

LaTeX for Word:

```
-\left(P_{\mathrm{ch,max}}(\mathrm{SoC}) + P_{b0}\right) + P_{\mathrm{pv},s} \;\le\; P_v \;\le\; P_{\mathrm{dis,max}}(\mathrm{SoC}) - P_{b0} + P_{\mathrm{pv},s}
```

The VSG can only deliver what the BESS has left after the EMS dispatch, plus the PV share. The SoC-dependent limits taper linearly near the SoC bounds (0.10–0.95). The BESS supplies the remainder, P_b = P_b0 + P_v − P_pv,s.

Where:

- $P_{\mathrm{ch,max}},\ P_{\mathrm{dis,max}}$: SoC-dependent charge and discharge limits
- $P_{b0}$: BESS power dispatched by the EMS
- $P_{\mathrm{pv},s}$: PV share of the support

### PV share of the support

*Proposal (3.16a)*

$$ T_{\mathrm{pv}}\,\frac{dP_{\mathrm{pv},s}}{dt} = \mathrm{clip}\!\left(\alpha\,P_{v,\mathrm{req}},\ -P_{\mathrm{pv},0},\ d\,P_{\mathrm{MPP}}\right) - P_{\mathrm{pv},s} $$

LaTeX for Word:

```
T_{\mathrm{pv}}\,\frac{dP_{\mathrm{pv},s}}{dt} = \mathrm{clip}\!\left(\alpha\,P_{v,\mathrm{req}},\ -P_{\mathrm{pv},0},\ d\,P_{\mathrm{MPP}}\right) - P_{\mathrm{pv},s}
```

The de-loaded PV plant follows a fraction α of the VSG power request through an 80 ms lag, bounded by its reserve upwards and by its base output downwards. clip(x, a, b) limits x to [a, b].

Where:

- $\alpha$: PV share (0–1, scheduled by the agent)
- $T_{\mathrm{pv}}$: PV lag, 80 ms
- $d\,P_{\mathrm{MPP}}$: PV reserve (d = 0.15 of the maximum power point)
- $P_{\mathrm{pv},0}$: PV base output, $(1 - d)\,P_{\mathrm{MPP}}$

## Part C. Converter-headroom feasibility (proposal Section 3.6, IREA Section V)

### Summed headroom requirement (Study 1)

*Proposal (3.17)*

$$ h_{\mathrm{req}} = 2J\,\frac{\mathrm{RoCoF}_{\max}}{f_0} + D\,\frac{\Delta f_{\max}}{f_0} = 0.08\,J + 0.01\,D $$

LaTeX for Word:

```
h_{\mathrm{req}} = 2J\,\frac{\mathrm{RoCoF}_{\max}}{f_0} + D\,\frac{\Delta f_{\max}}{f_0} = 0.08\,J + 0.01\,D
```

Headroom needed if the RoCoF limit (2 Hz/s) and the deviation limit (0.5 Hz) are reached at the same time. One second of inertia commits as much headroom as 8 pu of damping.

Where:

- $h_{\mathrm{req}}$: required headroom (pu)
- $f_0$: nominal frequency, 50 Hz

### Summed headroom requirement (Study 2 notation)

*IREA (7)*

$$ h_{\mathrm{req,sum}} = 2J_v\,\mathrm{RoCoF}_{\mathrm{lim}} + D_v\,\Delta f_{\mathrm{lim}} $$

LaTeX for Word:

```
h_{\mathrm{req,sum}} = 2J_v\,\mathrm{RoCoF}_{\mathrm{lim}} + D_v\,\Delta f_{\mathrm{lim}}
```

The same rule as (3.17), written for Study 2. RoCoF_lim and Δf_lim are in per unit of f₀ (divided by 50 Hz), as in the code.

### Available headroom (Study 1)

*Proposal (3.18)*

$$ h_{\mathrm{avail}} = \frac{S_{\mathrm{rated}} - \left|P_{\mathrm{sch}} + p_{\mathrm{dr}}\,S_{\mathrm{base}}\right|}{S_{\mathrm{base}}} $$

LaTeX for Word:

```
h_{\mathrm{avail}} = \frac{S_{\mathrm{rated}} - \left|P_{\mathrm{sch}} + p_{\mathrm{dr}}\,S_{\mathrm{base}}\right|}{S_{\mathrm{base}}}
```

Converter capacity left after the scheduled power and the droop response.

### Proportional derating

*Proposal (3.19) · IREA (9)*

$$ \left(J_{\mathrm{eff}},\,D_{\mathrm{eff}}\right) = \left(J,\,D\right)\cdot\min\!\left(1,\ \frac{h_{\mathrm{avail}}}{h_{\mathrm{req}}}\right) $$

LaTeX for Word:

```
\left(J_{\mathrm{eff}},\,D_{\mathrm{eff}}\right) = \left(J,\,D\right)\cdot\min\!\left(1,\ \frac{h_{\mathrm{avail}}}{h_{\mathrm{req}}}\right)
```

If the requirement exceeds the available headroom, both parameters are scaled by the same factor, keeping their ratio. IREA writes it as (J_v, D_v) ← (J_v, D_v)·min(1, h/h_req).

### Direction-aware headroom (Study 2)

*Proposal (3.20) · IREA (6)*

$$ h_{\mathrm{up}} = \max\!\left(P_{\mathrm{dis,max}}(\mathrm{SoC}) - P_{b0},\ 0\right) + d\,P_{\mathrm{MPP}}, \qquad h_{\mathrm{dn}} = \max\!\left(P_{\mathrm{ch,max}}(\mathrm{SoC}) + P_{b0},\ 0\right) + P_{\mathrm{pv},0} $$

LaTeX for Word:

```
h_{\mathrm{up}} = \max\!\left(P_{\mathrm{dis,max}}(\mathrm{SoC}) - P_{b0},\ 0\right) + d\,P_{\mathrm{MPP}}, \qquad h_{\mathrm{dn}} = \max\!\left(P_{\mathrm{ch,max}}(\mathrm{SoC}) + P_{b0},\ 0\right) + P_{\mathrm{pv},0}
```

Upward headroom applies while the frequency is at or below nominal, downward headroom during over-frequency. A BESS already discharging for the EMS has little upward but much downward headroom.

Where:

- $h_{\mathrm{up}},\ h_{\mathrm{dn}}$: upward and downward headroom (pu)

### Time-separated (max) headroom requirement

*Proposal (3.21) · IREA (8)*

$$ h_{\mathrm{req,max}} = \max\!\left(2J_v\,\mathrm{RoCoF}_{\mathrm{lim}},\ D_v\,\Delta f_{\mathrm{band}}\right) \le h $$

LaTeX for Word:

```
h_{\mathrm{req,max}} = \max\!\left(2J_v\,\mathrm{RoCoF}_{\mathrm{lim}},\ D_v\,\Delta f_{\mathrm{band}}\right) \le h
```

The RoCoF peaks just after a step, when the deviation is still near zero, and the deviation peaks at the nadir, when the RoCoF is zero, so each mechanism is sized at its own peak. With RoCoF_lim = 1/50 pu/s and Δf_band = 0.2/50 pu this is max(0.04 J_v, 0.004 D_v) ≤ h. The clipping variant uses J_v ≤ h/(2 RoCoF_lim) and D_v ≤ h/Δf_band separately.

Where:

- $h$: headroom in the direction of the event, $h_{\mathrm{up}}$ or $h_{\mathrm{dn}}$ (pu)

## Part D. Learning formulation (proposal Sections 3.7–3.8, IREA Section VI)

### Residual action mapping (Study 2)

*Proposal (3.22)*

$$ J_v = \begin{cases} J_0 + a_1\left(J_{\mathrm{ub}} - J_0\right), & a_1 \ge 0 \\ J_0 + a_1\left(J_0 - J_{\min}\right), & a_1 < 0 \end{cases} $$

LaTeX for Word:

```
J_v = \begin{cases} J_0 + a_1\left(J_{\mathrm{ub}} - J_0\right), & a_1 \ge 0 \\ J_0 + a_1\left(J_0 - J_{\min}\right), & a_1 < 0 \end{cases}
```

a = 0 reproduces the validation-tuned VSG (J_0 = 3 s, D_0 = 15 pu, α_0 = 1.0), and a = ±1 moves the parameter to its projected bound. D_v and α are mapped in the same way with a_2 and a_3.

Where:

- $a_1 \in [-1, 1]$: first action component
- $J_{\mathrm{ub}}$: projected (feasible) upper bound
- $J_{\min}$: lower bound of the range

### Interval cost (Study 2)

*Proposal (3.23) · IREA (10)*

$$ c = w_f\,\frac{\left\langle\left(|\Delta f| - 0.2\right)_{+}^{2}\right\rangle}{0.5^{2}} + w_{\mathrm{in}}\,\frac{\left\langle\Delta f^{2}\right\rangle}{0.5^{2}} + w_r\left\langle\left(|\mathrm{RoCoF}| - 1\right)_{+}^{2}\right\rangle + w_{\mathrm{fast}}\,\frac{\left\langle\left(P_v - P_{\mathrm{set}}\right)^{2}\right\rangle}{P_{b,\max}^{2}} + w_b\,\frac{\left\langle\Delta P_b^{2}\right\rangle}{P_{b,\max}^{2}} + w_s\,\frac{\langle\mathrm{sat}\rangle}{0.05} + w_v\,\mathrm{viol} $$

LaTeX for Word:

```
c = w_f\,\frac{\left\langle\left(|\Delta f| - 0.2\right)_{+}^{2}\right\rangle}{0.5^{2}} + w_{\mathrm{in}}\,\frac{\left\langle\Delta f^{2}\right\rangle}{0.5^{2}} + w_r\left\langle\left(|\mathrm{RoCoF}| - 1\right)_{+}^{2}\right\rangle + w_{\mathrm{fast}}\,\frac{\left\langle\left(P_v - P_{\mathrm{set}}\right)^{2}\right\rangle}{P_{b,\max}^{2}} + w_b\,\frac{\left\langle\Delta P_b^{2}\right\rangle}{P_{b,\max}^{2}} + w_s\,\frac{\langle\mathrm{sat}\rangle}{0.05} + w_v\,\mathrm{viol}
```

Cost of one 50 ms decision interval. It penalises frequency outside ±0.2 Hz, RoCoF above 1 Hz/s, fast VSG power above its set-point, BESS power, converter saturation and protection-limit violations. Weights (w_f, w_in, w_r, w_fast, w_b, w_s, w_v) = (1, 0.02, 0.5, 2, 0.1, 2, 1); the episode return is R = −Σc. IREA writes ΔP_bess for ΔP_b.

Where:

- $\langle\cdot\rangle$: mean over the interval
- $(x)_{+}$: $\max(x, 0)$
- $\Delta f$: frequency deviation (Hz)
- $\mathrm{RoCoF}$: rate of change of frequency (Hz/s)
- $\mathrm{sat}$: 1 while the converter is at its limit, else 0
- $\mathrm{viol}$: protection-limit violation indicator
- $P_{b,\max}$: BESS power rating

### TD3 critic target

*Proposal (3.24)*

$$ y = r + \gamma \min_{i=1,2} Q_{\phi'_i}\!\left(s',\ \mu_{\theta'}(s') + \varepsilon\right), \qquad \varepsilon \sim \mathrm{clip}\!\left(\mathcal{N}(0,\sigma^{2}),\ -c,\ c\right) $$

LaTeX for Word:

```
y = r + \gamma \min_{i=1,2} Q_{\phi'_i}\!\left(s',\ \mu_{\theta'}(s') + \varepsilon\right), \qquad \varepsilon \sim \mathrm{clip}\!\left(\mathcal{N}(0,\sigma^{2}),\ -c,\ c\right)
```

TD3 trains two critics and uses the smaller target to avoid overestimation, and adds clipped noise to the target action (Fujimoto et al., 2018). DDPG uses one critic, y = r + γ Q_φ'(s', μ_θ'(s')).

Where:

- $\gamma$: discount factor, 0.99
- $Q_{\phi'_i}$: target critics
- $\mu_{\theta'}$: target actor
- $\sigma,\ c$: target smoothing noise and clip (0.1, 0.3 in Study 1; 0.2, 0.5 in Study 2)

## Part E. Metrics and oracle bound (proposal Section 3.9, IREA Section VI.B)

### Frequency error integrals

*Proposal (3.25)*

$$ \mathrm{IAE} = \int_0^{T} |\Delta f|\,dt, \qquad \mathrm{ISE} = \int_0^{T} \Delta f^{2}\,dt, \qquad \mathrm{ITAE} = \int_0^{T} t\,|\Delta f|\,dt $$

LaTeX for Word:

```
\mathrm{IAE} = \int_0^{T} |\Delta f|\,dt, \qquad \mathrm{ISE} = \int_0^{T} \Delta f^{2}\,dt, \qquad \mathrm{ITAE} = \int_0^{T} t\,|\Delta f|\,dt
```

Integral absolute, squared and time-weighted absolute frequency error over an episode of length T (Study 1 metrics).

### Oracle gain

*Proposal (3.26)*

$$ G_{\mathrm{oracle}} = \frac{1}{N}\sum_{i=1}^{N}\max_{k} R_{ik} - \max_{k}\,\frac{1}{N}\sum_{i=1}^{N} R_{ik} $$

LaTeX for Word:

```
G_{\mathrm{oracle}} = \frac{1}{N}\sum_{i=1}^{N}\max_{k} R_{ik} - \max_{k}\,\frac{1}{N}\sum_{i=1}^{N} R_{ik}
```

Best setting chosen per scenario minus the best single setting. If G_oracle is small, no scenario-level adaptive controller can improve much on a tuned VSG. In Study 2: 24 settings, 40 validation scenarios, gain 2.1 %.

Where:

- $R_{ik}$: return of fixed setting k on scenario i
- $N,\ K$: number of scenarios and settings

## Part F. Short expressions written inside the text

These appear inside sentences rather than as numbered equations.

$$ \Delta\omega = \frac{f - f_0}{f_0} $$

*per-unit frequency deviation (Section 3.5.1)*

```
\Delta\omega = \frac{f - f_0}{f_0}
```

$$ P_{\mathrm{pv},0} = (1 - d)\,P_{\mathrm{MPP}} $$

*de-loaded PV base output (Section 3.3)*

```
P_{\mathrm{pv},0} = (1 - d)\,P_{\mathrm{MPP}}
```

$$ k_{\mathrm{NOCT}} = \frac{\mathrm{NOCT} - 20}{800} $$

*temperature-rise coefficient in Study 2 (Section 3.3)*

```
k_{\mathrm{NOCT}} = \frac{\mathrm{NOCT} - 20}{800}
```

$$ P_b = P_{b0} + P_v - P_{\mathrm{pv},s} $$

*BESS power (Section 3.5.2)*

```
P_b = P_{b0} + P_v - P_{\mathrm{pv},s}
```

$$ \Delta P_{e,d} = \Delta P_{\mathrm{net}} - P_v $$

*diesel electrical power (model code; used in 3.14)*

```
\Delta P_{e,d} = \Delta P_{\mathrm{net}} - P_v
```

$$ \frac{K_s}{K_s + K_d} = \frac{2.0}{2.8} \approx 0.71 $$

*initial VSG share of a load step*

```
\frac{K_s}{K_s + K_d} = \frac{2.0}{2.8} \approx 0.71
```

$$ J_v \le \frac{h}{2\,\mathrm{RoCoF}_{\mathrm{lim}}}, \qquad D_v \le \frac{h}{\Delta f_{\mathrm{band}}} $$

*clipping derating (Section 3.6, IREA V.C)*

```
J_v \le \frac{h}{2\,\mathrm{RoCoF}_{\mathrm{lim}}}, \qquad D_v \le \frac{h}{\Delta f_{\mathrm{band}}}
```

$$ y = r + \gamma\,Q_{\phi'}\!\left(s',\ \mu_{\theta'}(s')\right) $$

*DDPG critic target (Section 3.8)*

```
y = r + \gamma\,Q_{\phi'}\!\left(s',\ \mu_{\theta'}(s')\right)
```

$$ R = -\sum_t c_t $$

*episode return (Section 3.7)*

```
R = -\sum_t c_t
```
