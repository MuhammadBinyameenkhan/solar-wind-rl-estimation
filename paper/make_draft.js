// Generates paper/IREA_paper_draft.docx from the study results.   Run: node paper/make_draft.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, HeadingLevel, ShadingType, BorderStyle, PageNumber, Footer, LevelFormat,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const FIG = (f) => path.join(ROOT, "results", "figures", f);
const FONT = "Times New Roman";
const TEXT_W = 9026; // A4 width 11906 − 2 × 1440 margins (DXA)

// ---------- helpers ----------
function runs(parts) {
  return parts.map((p) => {
    if (typeof p === "string") return new TextRun({ text: p, font: FONT, size: 20 });
    return new TextRun({ text: p.t, bold: !!p.b, italics: !!p.i, font: FONT, size: p.size || 20,
      shading: p.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined, superScript: !!p.sup, subScript: !!p.sub });
  });
}
const P = (...parts) => new Paragraph({ children: runs(parts), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 120, line: 276 } });
const TODO = (t) => ({ t: `[AUTHOR: ${t}]`, hl: true });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT, size: 22, bold: true })],
  spacing: { before: 240, after: 120 } });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT, size: 20, bold: true, italics: true })],
  spacing: { before: 160, after: 80 } });
const EQ = (txt, n) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
  children: [new TextRun({ text: txt, font: FONT, size: 20, italics: true }), new TextRun({ text: `\t(${n})`, font: FONT, size: 20 })],
  tabStops: [{ type: "right", position: TEXT_W }] });
const BUL = (...parts) => new Paragraph({ children: runs(parts), numbering: { reference: "bul", level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 } });
function FIGURE(file, wpx, hpx, widthIn, caption) {
  const buf = fs.readFileSync(FIG(file));               // PNG header: width @16, height @20
  wpx = buf.readUInt32BE(16); hpx = buf.readUInt32BE(20);
  const w = Math.round(widthIn * 96), h = Math.round(w * hpx / wpx);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG(file)), transformation: { width: w, height: h },
        altText: { title: caption.slice(0, 40), description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: runs([{ t: caption, size: 18 }]) }),
  ];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(caption, header, rows, widths) {
  const tot = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, j, isHead) => new TableCell({ borders, width: { size: widths[j], type: WidthType.DXA },
    shading: isHead ? { fill: "E8E8E8", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ alignment: j === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: [new TextRun({ text: String(txt), font: FONT, size: 17, bold: isHead })] })] });
  const tRows = [header, ...rows].map((r, i) => new TableRow({ tableHeader: i === 0,
    children: r.map((c, j) => cell(c, j, i === 0)) }));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 }, keepNext: true,
      children: runs([{ t: caption, size: 18, b: true }]) }),
    new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths, rows: tRows }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

// ---------- content ----------
const C = [];
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({
  text: "Toward Feasible Synthetic Inertia: A Headroom-Constrained Assessment of Reinforcement-Learning Virtual Synchronous Generator Control in a Low-Inertia PV–Wind–BESS Microgrid Using Real Meteorological Data",
  font: FONT, size: 28, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, children: runs([TODO("Author name(s), affiliation(s), e-mail of corresponding author")]) }));
C.push(new Paragraph({ spacing: { after: 120 }, children: [] }));

C.push(P({ t: "Abstract – ", b: true },
  "Virtual synchronous generators (VSGs) let battery and photovoltaic (PV) inverters emulate the inertia and damping that low-inertia microgrids lack, and reinforcement learning (RL) has been proposed to adapt these parameters online. Two questions are rarely tested together: whether the inertia and damping an adaptive controller commits can actually be delivered by the available battery and PV headroom, and whether RL improves on a properly tuned fixed VSG. This paper studies a 2 MVA PV–wind–battery–diesel microgrid driven by one year (2024) of hourly ERA5 wind and NASA POWER solar data for a site in Nakhon Ratchasima, Thailand. A direction-aware headroom projection is proposed that bounds the virtual damping by the power required at the edge of a ±0.2 Hz band and the virtual inertia by the power required at the rate-of-change-of-frequency limit. TD3 and DDPG agents (5 seeds × 1000 episodes each) are trained as residual policies on a validation-tuned fixed VSG and evaluated on 200 held-out multi-event scenarios against six benchmarks, with Holm-corrected Wilcoxon tests. Without the projection, the learned TD3 policy commits infeasible inertia or damping for 5.07 s of every 30 s episode; with it, 0.02 s (p ≈ 10",
  { t: "−32", sup: true }, "), at negligible cost for the tuned VSG. An oracle bound shows that scenario-level adaptation can improve on the tuned fixed VSG by at most 2.1 %, and neither RL agent beats it on the overall objective. The full model is independently re-implemented in MATLAB and reproduces the Python results to within 1.1×10",
  { t: "−7", sup: true }, " Hz."));
C.push(P({ t: "Keywords – ", b: true }, "Virtual synchronous generator, synthetic inertia, reinforcement learning, TD3, battery energy storage, headroom, low-inertia microgrid, frequency stability."));

// I. INTRODUCTION
C.push(H1("I. Introduction"));
C.push(P("Replacing synchronous generation with inverter-based photovoltaic (PV) and wind generation reduces the rotational inertia that limits the initial rate of change of frequency (RoCoF) and the frequency nadir after a power imbalance [1]. In small isolated microgrids, where a single diesel unit may provide all of the physical inertia, a step change of a few hundred kilowatts can push frequency outside protection limits within a second. Grid-forming inverters controlled as virtual synchronous generators (VSGs) address this by emulating the swing equation of a synchronous machine, with a virtual inertia H and damping D that are set in software [2], [3]."));
C.push(P("Because H and D are software parameters, several authors have proposed changing them online: bang-bang schemes that switch inertia depending on whether the frequency is moving away from or towards nominal [4], rule-based or fuzzy adaptive laws, and, more recently, reinforcement-learning (RL) agents that learn a parameter schedule from simulation [", TODO("cite RL-VSG works from your PRISMA review, e.g. Oboreh-Snapps et al. 2024, Zhou et al. 2026"), "]. Two aspects receive less attention. First, every unit of virtual inertia or damping is a power commitment: a battery (BESS) at low state of charge, or one already dispatched by the energy management system, may not be able to deliver it. Second, adaptive controllers are often compared with a fixed VSG whose parameters were not tuned for the same objective, which makes the reported gains hard to interpret."));
C.push(P(TODO("Summarise the PRISMA-style literature review here: databases, search string, numbers screened/included (PRISMA 2020 [12]), and the gap table. State what each closest competitor does and does not cover.")));
C.push(P("This paper contributes:"));
C.push(BUL({ t: "A direction-aware headroom feasibility projection ", b: true }, "for VSG parameters, which bounds D by the damping power at the edge of a ±0.2 Hz band and H by the inertial power at the RoCoF limit, using the upward or downward BESS + PV headroom depending on the direction of the event."));
C.push(BUL({ t: "A real-data operating envelope ", b: true }, "built from 2024 ERA5 wind and NASA POWER solar data, with a rule-based EMS that commits BESS power, weekly-block train/validation/test splits and an adequacy screen."));
C.push(BUL({ t: "An oracle bound ", b: true }, "that estimates, before any RL training, how much scenario-level adaptation of (H, D) can gain over the best fixed VSG."));
C.push(BUL({ t: "A rigorous benchmark ", b: true }, "of TD3 and DDPG residual policies (5 seeds × 1000 episodes) against six controllers, including a validation-tuned fixed VSG, with Pareto and Holm-corrected statistical analysis, and an ablation of the projection."));
C.push(BUL({ t: "An independent MATLAB implementation ", b: true }, "that reproduces the Python results, as a basis for the circuit-level Simscape validation."));

// II. SYSTEM
C.push(H1("II. System Description and Modelling"));
C.push(P("The study system (Fig. 1) is an isolated microgrid with a 2 MVA, 50 Hz base: a 1.0 MW wind turbine, a 0.8 MW PV plant operated with de-loaded maximum power point tracking (15 % headroom), a 0.5 MW / 2 MWh BESS whose inverter is controlled as a grid-forming VSG, and a 0.5 MW diesel generator that provides the only physical inertia (H = 2 s on its own base, 0.5 s on the system base). Table I lists the parameters."));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 }, children: runs([TODO("insert Fig. 1 — single-line diagram: diesel SG, wind (grid-following), de-loaded PV and BESS behind the VSG inverter, load bus, EMS and RL/VSG controller"), { t: "  Fig. 1. Microgrid single-line diagram.", size: 18 }]) }));
C.push(...TABLE("TABLE I. Study system and model parameters",
  ["Component", "Rating / parameter", "Value"],
  [["System", "Base power, frequency", "2.0 MVA, 50 Hz"],
   ["Wind turbine", "Rating; class; hub height", "1.0 MW; IEC III (cut-in 2.5 m/s, rated 10 m/s); 100 m"],
   ["PV plant", "Rating; de-loading; headroom release lag", "0.8 MW; 15 % of P_MPP; 80 ms"],
   ["BESS", "Power; energy; SoC limits; efficiency", "0.5 MW; 2 MWh; 0.10–0.95; 0.95/0.95"],
   ["Diesel SG", "Rating; inertia; droop; T_g, T_e", "0.5 MW; 2 s (own base); 5 %; 0.2 s, 0.5 s"],
   ["Synchronising coeff.", "Diesel K_d; VSG K_s (system base)", "0.8 pu; 2.0 pu"],
   ["Secondary control", "Integral gain, diesel and BESS", "2.0 pu/(pu·s)"],
   ["VSG parameter range", "H_v; D_v; PV share α", "0.2–8 s; 0–50 pu; 0–1"],
   ["Load", "Range; damping", "0.3–0.8 MW; 1 pu"],
   ["Disturbances", "Per 30 s episode", "2–3 steps of 0.2–0.4 MW, net ≤ ±0.4 MW"]],
  [2000, 3426, 3600]));
C.push(H2("A. Two-machine RMS model"));
C.push(P("The diesel synchronous generator (SG) and the VSG are modelled as two voltage sources sharing the load bus through synchronising coefficients K_d and K_s; wind and the de-loaded PV base output are grid-following power injections. With all quantities in per-unit of the system base and δ the angle of the VSG relative to the SG, the network gives the VSG power and the bus frequency:"));
C.push(EQ("P_v = K_s (K_d δ + ΔP_net) / (K_d + K_s),     ΔP_net = ΔP_L − ΔP_w + D_L P_L0 Δω_b", 1));
C.push(EQ("Δω_b = (K_d Δω_d + K_s Δω_v) / (K_d + K_s)", 2));
C.push(P("The SG and the virtual rotor obey the swing equations [14]"));
C.push(EQ("2H_d dΔω_d/dt = ΔP_m − ΔP_e,d − D_d (Δω_d − Δω_b)", 3));
C.push(EQ("2H_v dΔω_v/dt = P_set − P_v − D_v Δω_v,     dδ/dt = ω_0 (Δω_v − Δω_d)", 4));
C.push(P("where ΔP_m follows a droop governor with first-order governor and engine dynamics, and P_set is the VSG power set-point moved by BESS secondary control (an integral of the frequency error, as for the diesel AGC). At the instant of a load step the VSG therefore takes K_s/(K_s + K_d) ≈ 71 % of the step, which is the defining grid-forming behaviour."));
C.push(P("The VSG output is limited by the SoC-dependent BESS power limits and the PV headroom, P_v ∈ [−(P_ch,max + P_b0) + P_pv,s, P_dis,max − P_b0 + P_pv,s], where P_b0 is the BESS base power set by the EMS and P_pv,s the PV share of the support (α P_v, released with an 80 ms lag). When the limit is reached the VSG becomes current-limited and an angle anti-windup holds δ. The model is integrated with a symplectic Euler scheme at 2 ms; frequency is measured through a 20 ms low-pass (PLL) filter."));
C.push(H2("B. Operating point and energy management"));
C.push(P("Each hourly operating point sets the available wind power (density-corrected power curve [19]), the PV maximum power and the load. A rule-based EMS dispatches the BESS: it charges from renewable surplus before curtailing wind and PV, and discharges to keep the diesel at 60 % of rating, using up to 80 % of the SoC-dependent BESS limit. The BESS base power P_b0 therefore occupies part of the headroom that synthetic inertia needs, most visibly in the evening peak. An adequacy screen removes operating points at which load would be shed or the largest cumulative load increase exceeds the diesel spare plus VSG headroom (7.4 % of test draws)."));

// III. DATA
C.push(H1("III. Real Meteorological Data"));
C.push(P("Wind and solar data are taken from the source that is stronger for each variable. The 100 m wind components (u100, v100) come from ERA5 [7] on a 2 × 2 grid around the site (14.98° N, 102.10° E, 226 m), interpolated bilinearly. Hourly global horizontal irradiance and 2 m temperature come from NASA POWER [8]; local-solar-time stamps are converted to UTC, and the irradiance peaks at 11:00 local time as expected. Air density uses the NASA POWER temperature and the barometric pressure at the site elevation, because the ERA5 extract has no temperature or pressure. The two sources overlap for 8777 hours of 2024 (Fig. 2)."));
C.push(P("The site has low wind: ERA5 100 m wind averages 4.2 m/s and MERRA-2 50 m wind from NASA POWER 5.1 m/s, with an hourly correlation of 0.78. A low-wind IEC class III turbine with a 100 m hub (ERA5's own reference height) is therefore assumed, giving a capacity factor of 9.5 % versus 4.4 % for a generic 12 m/s-rated machine. Because only one year is available, the data are split into weekly blocks (five training, one validation, one test week in every seven), so that all seasons appear in every split and whole weeks limit temporal leakage (Table II). The load is a synthetic daily, weekly and seasonal profile scaled to 0.3–0.8 MW so that the evening peak fits the firm capacity.", TODO("replace with a measured load profile if available")));
C.push(...TABLE("TABLE II. Hybrid dataset (2024), per split",
  ["Split", "Hours", "Hub wind (m/s)", "Wind CF", "PV CF", "Mean GHI (W/m²)", "Mean load (MW)", "RES share"],
  [["All", "8777", "4.19", "9.5 %", "17.3 %", "213", "0.64", "36 %"],
   ["Train", "6425", "4.38", "10.5 %", "17.2 %", "212", "0.64", "37 %"],
   ["Validation", "1176", "3.71", "7.7 %", "17.1 %", "211", "0.64", "33 %"],
   ["Test", "1176", "3.67", "6.3 %", "18.1 %", "223", "0.64", "32 %"]],
  [1226, 900, 1150, 1000, 1000, 1350, 1250, 1150]));
C.push(...FIGURE("fig_data_overview.png", 1180, 879, 6.0, "Fig. 2. Daily means of the hourly operating points (wind from ERA5, PV from NASA POWER, synthetic load); validation and test weeks shaded."));

// IV. FEASIBILITY + FORMULATION
C.push(H1("IV. Feasible Synthetic Inertia and Control Formulation"));
C.push(H2("A. Direction-aware headroom projection"));
C.push(P("Let h denote the fast reserve the VSG can actually deliver in the direction of the current event. While the frequency is at or below nominal it is the upward headroom, and during an over-frequency event the downward headroom:"));
C.push(EQ("h_up = max(P_dis,max(SoC) − P_b0, 0) + d·P_MPP,     h_dn = max(P_ch,max(SoC) + P_b0, 0) + P_pv,0", 5));
C.push(P("A VSG with damping D delivers D·Δf_band at the edge of the permitted band Δf_band = 0.2 Hz (the maximum steady-state deviation used in the European system operation guideline [13]), and a virtual inertia H delivers 2H·RoCoF_lim at the RoCoF limit of 1 Hz/s. Both must fit within h, which gives the feasible bounds (per unit)"));
C.push(EQ("D ≤ D_ub = h / Δf_band,     H ≤ H_ub = h / (2·RoCoF_lim)", 6));
C.push(P("The commanded parameters pass a first-order rate limiter (τ = 0.25 s), because abrupt parameter changes inject transients, and are then clipped to (6). The clip follows the rate limiter so that feasibility takes priority over smoothness: a reduction required by shrinking headroom is applied immediately. An ", { t: "infeasible commitment", i: true }, " is any instant at which max(D·Δf_band, 2H·RoCoF_lim) > h; its total duration per episode is used to measure what the projection prevents."));
C.push(H2("B. Episodes and objective"));
C.push(P("Each 30 s episode starts from a sampled hourly operating point and contains 2–3 load steps of 0.2–0.4 MW (75 % increases), at least 7 s apart, with the net change kept within ±0.4 MW; the SoC, AGC state and BESS set-point carry over between events. Controllers update (H, D, α) every 50 ms. The per-interval cost penalises frequency only outside the ±0.2 Hz band and RoCoF only above 1 Hz/s, plus the VSG fast power above its secondary set-point (the inertial and damping response that H and D control), the total BESS power, current-limit saturation and protection-limit violations:"));
C.push(EQ("c = w_f⟨(|Δf|−0.2)₊²⟩/0.5² + w_in⟨Δf²⟩/0.5² + w_r⟨(|RoCoF|−1)₊²⟩ + w_fast⟨(P_v−P_set)²⟩/P_b,max² + w_b⟨ΔP_bess²⟩/P_b,max² + w_s⟨sat⟩/0.05 + w_v·viol", 7));
C.push(P("with weights (w_f, w_in, w_r, w_fast, w_b, w_s, w_v) = (1, 0.02, 0.5, 2, 0.1, 2, 1). The episode return is −Σc (objective return). The weights were calibrated so that the best fixed VSG has an interior damping (D = 15), i.e. the objective has a genuine trade-off between frequency quality and BESS effort. With a plain quadratic frequency penalty on single events, maximum damping was optimal and the problem was trivial; this formulation study is reported in the repository documentation."));

// V. METHODS
C.push(H1("V. Learning Agents, Benchmarks and Evaluation"));
C.push(H2("A. Residual TD3 and DDPG agents"));
C.push(P("The agent observes 16 normalised quantities (frequency deviation and RoCoF, VSG power, virtual-rotor slip, upward, downward and PV headroom, SoC, wind, PV and diesel power, diesel spare, load, and the currently applied H, D and α) and outputs a ∈ [−1, 1]³. A residual mapping is used [9]: a = 0 gives the validation-tuned fixed VSG and a = ±1 moves to the projected bounds. The actor's output layer is initialised to zero so that the untrained policy is exactly this base controller, and a small penalty on ‖a‖² acts as a trust region. These two regularisers (with an action-rate penalty) are used for training only and are excluded from the reported objective return. TD3 [5] and DDPG [6] share the same code; DDPG disables TD3's twin critics, target smoothing and delayed actor updates. Table III lists the settings."));
C.push(...TABLE("TABLE III. Training settings",
  ["Setting", "Value"],
  [["Actor / critic networks", "MLP 256–256, ReLU; tanh output (actor)"],
   ["Learning rates", "actor 1×10⁻⁴, critic 3×10⁻⁴ (Adam)"],
   ["Discount, target update", "γ = 0.99, τ = 0.005"],
   ["Batch, buffer, warm-up", "256; 10⁶; 10 000 random steps"],
   ["Update ratio", "one gradient update every 2 environment steps"],
   ["Exploration", "Gaussian, σ 0.10 → 0.03 (linear)"],
   ["TD3 specifics", "twin critics, target noise 0.2 (clip 0.5), policy delay 2"],
   ["Budget", "1000 episodes × 30 s (600 decisions each) × 5 seeds per configuration"],
   ["Model selection", "best mean return on 20 fixed validation scenarios, every 50 episodes (episode 0 included)"]],
  [3200, 5826]));
C.push(H2("B. Benchmarks"));
C.push(P("Six benchmarks share the 50 ms decision grid and the rate limiter: diesel only (no support); grid-following BESS droop (fast frequency response without inertia); a standard VSG (H = 3 s, D = 20); the validation-tuned fixed VSG (grid search over H, D and α; H = 3 s, D = 15, α = 1.0), with and without the projection; a bang-bang alternating-inertia VSG [4]; and a RoCoF-adaptive VSG. All gains were tuned on the validation weeks; the adaptive VSG's best gains were zero, i.e. it reduces to the standard VSG."));
C.push(H2("C. Evaluation protocol"));
C.push(P("All controllers and seeds are evaluated on the same 200 test scenarios drawn from the test weeks. Metrics are the worst-event frequency nadir, the maximum RoCoF over a 100 ms window, BESS energy throughput, current-limit saturation time, infeasible-commitment time and the objective return. RL results are averaged over seeds per scenario, and differences are tested with paired Wilcoxon signed-rank tests [10] with Holm correction [11] over all comparisons; multiple seeds follow the recommendations of [18]. To bound what any adaptive scheduler could achieve, an oracle selects, separately for each of 40 validation scenarios, the best of 24 fixed (H, D) settings, and is compared with the best single fixed setting."));

// VI. RESULTS
C.push(H1("VI. Results"));
C.push(H2("A. How much can adaptation gain? (oracle bound)"));
C.push(P("On 40 validation scenarios, the best single fixed VSG (H = 3 s, D = 15) achieves an objective return of −94.66, and the per-scenario oracle −92.66: adaptive scheduling of (H, D) can improve the objective by at most 2.0 points, or 2.1 %. The oracle's damping hardly depends on the operating point (D ≈ 12–15 across low, medium and high headroom), because D = 15 needs only about 0.12 MW of damping power at the band edge, which fits even the lowest-headroom cases. Two mechanisms explain the small margin: the VSG instantly takes about 71 % of any step through its synchronising coefficient regardless of H and D, and secondary control restores the frequency within 10–20 s, leaving H and D to shape only a short transient."));
C.push(H2("B. Test-set comparison"));
C.push(P("Table IV summarises the 200 test scenarios. Without fast support the diesel-only system collapses in 97.5 % of scenarios, and BESS droop without inertia violates the 1 Hz/s RoCoF limit everywhere (5.5 Hz/s). All VSG variants keep the system stable. The tuned fixed VSG achieves the best objective return (−105.9); for all ten RL runs (TD3 and DDPG, five seeds each) the best validation checkpoint was the untrained policy, i.e. the tuned VSG itself, so model selection returns the base controller."));
C.push(...TABLE("TABLE IV. Test-set results (200 scenarios; RL averaged over 5 seeds)",
  ["Controller", "Nadir (Hz)", "RoCoF (Hz/s)", "BESS (kWh)", "Saturation (s)", "Infeasible (s)", "Return"],
  [["Fixed VSG, tuned", "0.573", "1.474", "0.775", "0.103", "2.330", "−105.9"],
   ["Fixed VSG, tuned + projection", "0.573", "1.479", "0.775", "0.123", "0.007", "−106.1"],
   ["TD3 / DDPG, validation-selected", "0.573", "1.479", "0.775", "0.123", "0.007", "−106.1"],
   ["Fixed VSG, standard (H 3, D 20)", "0.508", "1.452", "0.934", "0.126", "2.340", "−115.8"],
   ["Bang-bang VSG [4]", "0.505", "1.423", "0.936", "0.121", "2.989", "−116.4"],
   ["TD3, final policy", "0.522", "1.482", "0.849", "0.136", "0.019", "−122.0"],
   ["TD3 w/o projection, final", "0.540", "1.457", "0.832", "0.108", "5.069", "−124.2"],
   ["DDPG, final policy", "0.596", "1.594", "0.845", "0.128", "0.022", "−133.4"],
   ["BESS droop (no inertia)", "0.732", "5.520", "0.927", "0.645", "1.103", "−286.8"],
   ["Diesel only", "3.06*", "7.38", "0", "0", "0", "−557.7"]],
  [2826, 950, 1050, 1000, 1100, 1100, 1000]));
C.push(P({ t: "*97.5 % of episodes collapse. Saturation and infeasible-commitment times are per 30 s episode.", size: 17, i: true }));
C.push(P("The learned TD3 policies trade a lower nadir for more BESS energy. Against the tuned VSG the nadir is 0.061 Hz lower (better in 85 % of scenarios, p_Holm ≈ 7×10", { t: "−21", sup: true }, "), RoCoF is not significantly different, BESS energy is 0.067 kWh higher (p_Holm ≈ 10", { t: "−31", sup: true }, ") and the objective return is 13.5 points worse (p_Holm ≈ 6×10", { t: "−32", sup: true }, "). TD3 is clearly better than DDPG on nadir, RoCoF and return (all p_Holm < 10", { t: "−9", sup: true }, ")."));
C.push(...FIGURE("fig_response_sc32.png", 0, 0, 4.6, "Fig. 3. Test scenario 32 (load increase followed by a load rejection): frequency deviation, RoCoF, VSG power and scheduled virtual inertia."));
C.push(H2("C. What the feasibility projection prevents"));
C.push(P("Table V isolates the projection. Trained without it, TD3 learns to over-commit: on every seed the learned policy schedules inertia or damping that the headroom cannot deliver for 3.9–7.2 s of each 30 s episode (mean 5.07 s), more than the tuned fixed VSG (2.33 s). With the projection, this falls to 0.02 s (lower in 98 % of scenarios), and the nadir also improves. For the tuned fixed VSG the projection removes infeasible commitments (2.33 → 0.007 s) without changing the nadir and at a return cost of 0.13. The current-limit saturation time is slightly higher with the projection (0.12 vs 0.10 s per episode); lower damping lets the frequency drift further, so BESS secondary control raises the set-point more."));
C.push(...TABLE("TABLE V. Projection ablation (paired Wilcoxon tests, 200 test scenarios)",
  ["Comparison", "Metric", "With projection", "Without", "p-value"],
  [["TD3 final policy", "Infeasible commitments (s)", "0.019", "5.069", "6×10⁻³² (Holm)"],
   ["TD3 final policy", "Nadir (Hz)", "0.522", "0.540", "3×10⁻⁶ (Holm)"],
   ["TD3 final policy", "Objective return", "−122.0", "−124.2", "0.087 (Holm, n.s.)"],
   ["Tuned fixed VSG", "Infeasible commitments (s)", "0.007", "2.330", "4×10⁻⁷ (raw)"],
   ["Tuned fixed VSG", "Nadir (Hz)", "0.573", "0.573", "0.56 (raw, n.s.)"],
   ["Tuned fixed VSG", "Objective return", "−106.1", "−105.9", "0.004 (raw)"]],
  [1826, 2400, 1400, 1300, 2100]));
C.push(H2("D. Pareto comparison and learning dynamics"));
C.push(P("Fig. 4 places each controller against the attainable front of the 24 fixed VSG settings for three trade-offs. No fixed setting is at least as good as the TD3 policy on all four objectives (fast energy, band time, nadir, RoCoF) simultaneously, but its nadir is close to that of a fixed VSG with D ≈ 17; it is a different point on the same trade-off rather than a better one. The DDPG policy is dominated by the tuned fixed VSG. The learning curves (Fig. 5) show that both agents start at the base controller and move below it; TD3 degrades less and with less seed-to-seed spread. The available improvement (≈2 %) is smaller than the variation of returns across operating points and events, so the critic cannot resolve it reliably."));
C.push(...FIGURE("fig_pareto.png", 0, 0, 6.4, "Fig. 4. Controllers against the fixed-VSG family (grey) and its attainable front (dashed): band violation, nadir and RoCoF versus VSG fast energy. Error bars: ±1 s.d. over seeds."));
C.push(...FIGURE("fig_learning_curves.png", 0, 0, 4.2, "Fig. 5. Validation return during training (mean ± s.d. over 5 seeds); dashed: base controller (episode 0)."));
C.push(H2("E. MATLAB implementation and cross-validation"));
C.push(P("The complete model (dispatch with EMS, two-machine dynamics, BESS secondary control, projection, rate limiter and clipping, the exported TD3 actor, and the metrics) was re-implemented independently in MATLAB code that runs without toolboxes. Twelve test scenarios with their exact wind and load noise sequences were re-simulated for the tuned fixed VSG, the projected VSG and a trained TD3 policy (Table VI, Fig. 6). The traces of both fixed controllers are bit-identical to the Python results, and the TD3 traces differ by at most 1.1×10", { t: "−7", sup: true }, " Hz, attributable to single-precision arithmetic in the neural network; all metrics agree to within 0.01 %. The MATLAB code is the starting point for the circuit-level Simscape validation."));
C.push(...TABLE("TABLE VI. MATLAB vs Python (12 test scenarios, 30 s, 2–3 events each)",
  ["Controller", "max |ΔΔf| (Hz)", "max |ΔP_VSG| (MW)", "Mean nadir Py / MATLAB (Hz)", "Mean return Py / MATLAB"],
  [["Fixed VSG, tuned", "0", "0", "0.5402 / 0.5402", "−80.15 / −80.15"],
   ["Fixed VSG + projection", "0", "0", "0.5418 / 0.5418", "−80.46 / −80.46"],
   ["TD3 policy (seed 1, final)", "1.1×10⁻⁷", "6.3×10⁻⁸", "0.5020 / 0.5020", "−88.96 / −88.96"]],
  [2426, 1500, 1600, 1800, 1700]));
C.push(P({ t: "Computed with GNU Octave 8.4; ", size: 17, i: true }, TODO("re-run matlab/run_matlab_validation.m in MATLAB and state the release")));
C.push(...FIGURE("fig_matlab_validation.png", 0, 0, 6.0, "Fig. 6. MATLAB vs Python: frequency deviation for test scenario 1 (top) and per-scenario metrics for 36 runs (bottom)."));

// VII. DISCUSSION
C.push(H1("VII. Discussion"));
C.push(P({ t: "Feasibility. ", b: true }, "The projection addresses a practical failure mode: an unconstrained learner, rewarded for frequency quality, learns to promise inertia and damping that the BESS and PV cannot back up, and does so more than a hand-tuned controller. Because the projection costs essentially nothing for a well-tuned VSG, it can be applied to any adaptive VSG scheme, learning-based or not."));
C.push(P({ t: "When does RL pay off? ", b: true }, "In this microgrid a single well-tuned VSG is within about 2 % of the best scenario-wise choice, and residual TD3 and DDPG policies did not improve on it. This should not be read as a general verdict on RL. The margin is small here because the grid-forming VSG is strongly coupled to the bus, secondary control is fast, and the optimal parameters depend little on the operating point. Larger margins can be expected with weaker synchronising coupling, slow or absent secondary control, events that are large compared with the headroom, or uncertain plant parameters. The oracle bound proposed here provides a cheap test, before any training, of whether a given system is such a case, and it identifies a common weakness of RL-VSG comparisons that use untuned fixed baselines."));
C.push(P({ t: "Limitations. ", b: true }, "The plant is an RMS (phasor-averaged) single-bus model without inner current and voltage loops or reactive-power dynamics; the MATLAB re-implementation verifies the code but not the model fidelity, which requires the planned circuit-level Simscape validation. The load profile is synthetic, only one site and year are used, and the reward weights are a design choice (their calibration is documented). ", TODO("add Simscape results here if completed; otherwise keep as future work")));

// VIII. CONCLUSION
C.push(H1("VIII. Conclusion"));
C.push(P("A headroom-constrained assessment of RL-based VSG control was carried out for a low-inertia PV–wind–BESS–diesel microgrid driven by one year of real ERA5 and NASA POWER data. A direction-aware projection that bounds virtual damping and inertia by the power they require at the band and RoCoF limits removes infeasible commitments: from 5.07 s to 0.02 s per 30 s episode for a learned TD3 policy (p ≈ 10", { t: "−32", sup: true }, "), at negligible cost for a tuned fixed VSG. An oracle bound showed that adaptive scheduling of the VSG parameters can gain at most 2.1 % over the tuned fixed VSG in this system, and neither TD3 nor DDPG (5 seeds × 1000 episodes) exceeded it on the overall objective; TD3 found a different trade-off with a lower nadir and higher BESS use, while DDPG was dominated. An independent MATLAB implementation reproduced the results to within 1.1×10", { t: "−7", sup: true }, " Hz. Future work will validate the controllers in a circuit-level Simscape model, use measured load data and additional sites, and apply the oracle test to systems with weaker grid-forming coupling, where adaptive and learning-based control may pay off."));

C.push(H1("Data and Code Availability"));
C.push(P("All code, the 2024 input data, configuration files and scripts that reproduce every table and figure (Python, with a MATLAB re-implementation) are available at ", TODO("public GitHub URL or Zenodo DOI"), ". ERA5 data: Copernicus Climate Change Service; solar data: NASA POWER Project."));
C.push(H1("Acknowledgements"));
C.push(P(TODO("funding, supervisor, institution")));

// REFERENCES
C.push(H1("References"));
const REFS = [
  "F. Milano, F. Dörfler, G. Hug, D. J. Hill and G. Verbič, “Foundations and challenges of low-inertia systems,” in Proc. Power Systems Computation Conference (PSCC), Dublin, 2018.",
  "H. Bevrani, T. Ise and Y. Miura, “Virtual synchronous generators: A survey and new perspectives,” Int. J. Electr. Power Energy Syst., vol. 54, pp. 244–254, 2014.",
  "Q.-C. Zhong and G. Weiss, “Synchronverters: Inverters that mimic synchronous generators,” IEEE Trans. Ind. Electron., vol. 58, no. 4, pp. 1259–1267, 2011.",
  "J. Alipoor, Y. Miura and T. Ise, “Power system stabilization using virtual synchronous generator with alternating moment of inertia,” IEEE J. Emerg. Sel. Topics Power Electron., vol. 3, no. 2, pp. 451–458, 2015.",
  "S. Fujimoto, H. van Hoof and D. Meger, “Addressing function approximation error in actor-critic methods,” in Proc. 35th Int. Conf. Machine Learning (ICML), 2018.",
  "T. P. Lillicrap et al., “Continuous control with deep reinforcement learning,” in Proc. Int. Conf. Learning Representations (ICLR), 2016.",
  "H. Hersbach et al., “The ERA5 global reanalysis,” Q. J. R. Meteorol. Soc., vol. 146, no. 730, pp. 1999–2049, 2020.",
  "NASA Prediction Of Worldwide Energy Resources (POWER) Project, hourly data, https://power.larc.nasa.gov",
  "T. Silver, K. Allen, J. Tenenbaum and L. Kaelbling, “Residual policy learning,” arXiv:1812.06298, 2018.",
  "F. Wilcoxon, “Individual comparisons by ranking methods,” Biometrics Bulletin, vol. 1, no. 6, pp. 80–83, 1945.",
  "S. Holm, “A simple sequentially rejective multiple test procedure,” Scand. J. Statist., vol. 6, no. 2, pp. 65–70, 1979.",
  "M. J. Page et al., “The PRISMA 2020 statement: an updated guideline for reporting systematic reviews,” BMJ, vol. 372, n71, 2021.",
  "Commission Regulation (EU) 2017/1485 of 2 August 2017 establishing a guideline on electricity transmission system operation, Annex III (frequency quality defining parameters).",
  "P. Kundur, Power System Stability and Control. New York: McGraw-Hill, 1994.",
  "[AUTHOR: Oboreh-Snapps et al., 2024 — complete reference]",
  "[AUTHOR: Zhou et al., 2026 — complete reference]",
  "[AUTHOR: fuzzy-logic PV–wind–battery VSG paper — complete reference]",
  "P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup and D. Meger, “Deep reinforcement learning that matters,” in Proc. AAAI Conf. Artificial Intelligence, 2018.",
  "IEC 61400-12-1:2017, Wind energy generation systems — Part 12-1: Power performance measurements of electricity producing wind turbines.",
];
REFS.forEach((r, i) => C.push(new Paragraph({ spacing: { after: 60 }, indent: { left: 400, hanging: 400 },
  children: runs([`[${i + 1}] `, r.startsWith("[AUTHOR") ? { t: r, hl: true } : r]) })));

// ---------- document ----------
const doc = new Document({
  creator: "solar-wind-rl-estimation", title: "IREA paper draft",
  styles: { default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 20, bold: true, italics: true, font: FONT }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 500, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((b) => { const out = path.join(__dirname, "IREA_paper_draft.docx"); fs.writeFileSync(out, b); console.log("wrote", out); });
