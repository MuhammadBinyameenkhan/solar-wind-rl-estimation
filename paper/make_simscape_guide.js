// Step-by-step guide: IREA next steps and the Simscape (EMT) model.   Run: node paper/make_simscape_guide.js
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  ShadingType, BorderStyle, LevelFormat } = require("docx");

const FONT = "Calibri";
const W = 9026;
const R = (t, o = {}) => new TextRun({ text: t, font: o.code ? "Consolas" : FONT, size: o.size || 22, bold: o.b, italics: o.i,
  shading: o.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined });
const P = (...parts) => new Paragraph({ spacing: { after: 120, line: 288 },
  children: parts.map((p) => (typeof p === "string" ? R(p) : R(p.t, p))) });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 }, children: [R(t, { b: true, size: 32 })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 }, children: [R(t, { b: true, size: 26 })] });
const CODE = (...lines) => lines.map((l) => new Paragraph({ spacing: { after: 0 }, indent: { left: 360 },
  shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" }, children: [R(l, { code: true, size: 20 })] }));
let nl = 0; const lists = [];
const STEP = () => { const ref = `s${nl++}`; lists.push(ref); return (...parts) => new Paragraph({ numbering: { reference: ref, level: 0 },
  spacing: { after: 80, line: 288 }, children: parts.map((p) => (typeof p === "string" ? R(p) : R(p.t, p))) }); };
const BUL = (...parts) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60, line: 288 },
  children: parts.map((p) => (typeof p === "string" ? R(p) : R(p.t, p))) });
const b = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
function TABLE(header, rows, widths) {
  const cell = (t, j, h) => new TableCell({ borders: { top: b, bottom: b, left: b, right: b }, width: { size: widths[j], type: WidthType.DXA },
    shading: h ? { fill: "DCE6F2", type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ children: [R(String(t), { size: 19, b: h, code: !h && j === 1 && String(t).match(/^[a-z_.0-9]+$/) })] })] });
  return [new Table({ width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [header, ...rows].map((r, i) => new TableRow({ tableHeader: i === 0, children: r.map((c, j) => cell(c, j, i === 0)) })) }),
    new Paragraph({ spacing: { after: 120 }, children: [] })];
}
const C = [];

C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [R("IREA paper: next steps and the Simscape (EMT) model", { b: true, size: 36 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [R("Step-by-step guide for MATLAB R2021a with Simulink, Simscape and Simscape Electrical", { i: true })] }));

// ====================================================================== PART A
C.push(H1("Part A. What remains for the IREA paper"));
C.push(P("The manuscript (IREA_manuscript_PWP.docx) is complete except for the items highlighted in yellow. The order below finishes it with the least rework."));
{ const S = STEP();
  C.push(S({ t: "Confirm the circuit-level results in Simscape (Part B of this guide). ", b: true }, "The paper already contains EMT results from a script solver of the same circuit; running the Simscape model in MATLAB confirms them and removes the last technical placeholder (Section VIII, Limitations)."));
  C.push(S({ t: "Decide about retraining (optional). ", b: true }, "The feasibility-rule ablation shows that joint scaling is better than clipping. The paper already presents this as a recommendation; retraining the agents with it (about 3–4 h of computing, done on the Python side) would strengthen Section VII.4."));
  C.push(S({ t: "Fill the yellow items. ", b: true }, "Author list and order, author photographs, corresponding author, status of references [15] and [16], GitHub/Zenodo link, funding statement, and a check of every reference against its DOI (docs/PROPOSAL_REFERENCES.md)."));
  C.push(S({ t: "Read the IREA author guidelines. ", b: true }, "On the Praise Worthy Prize website, check the page limit, figure resolution, reference style, the copyright form and any publication charges. The manuscript already follows the layout of your IREMOS paper, which uses the same publisher template."));
  C.push(S({ t: "Make the code public. ", b: true }, "Create a public release of the repository (GitHub) and, ideally, a Zenodo DOI for it, then put the link in Data and Code Availability."));
  C.push(S({ t: "Write the cover letter. ", b: true }, "State the contribution in three sentences (oracle bound, feasibility rules, circuit-level validation), and declare the two related manuscripts (TREC under review, IREMOS submitted) and how this paper differs from them (hybrid plant, oracle, EMT validation)."));
  C.push(S({ t: "Final checks. ", b: true }, "Delete the yellow checklist box, accept all tracked changes, run a similarity check if your university provides one, and ask your advisor (Assoc. Prof. Dr. Anant Oonsivilai) and the co-authors to approve the final version."));
  C.push(S({ t: "Submit ", b: true }, "through the journal's online system, then answer the reviewers point by point when the reviews arrive.")); }

// ====================================================================== PART B
C.push(H1("Part B. Running the Simscape model, step by step"));
C.push(H2("B.1 What the model is"));
C.push(P("A three-phase 400 V, 50 Hz circuit of the hybrid microgrid, solved every 100 µs (electromagnetic-transient, EMT). It has exactly the parameters of the Python model, so any difference shows what the averaged (RMS) Python model neglects. The model is built automatically by a script; you do not draw any blocks."));
C.push(...TABLE(["Part of the microgrid", "How it is modelled in Simscape", "Blocks used"],
  [["BESS + PV support (VSG)", "Average-model converter: three controlled voltage sources behind the coupling impedance R_v + jX_v", "Controlled Voltage Source ×3, Three-Phase Series RLC Branch"],
   ["Diesel generator", "Internal voltage behind reactance X_d, with swing equation, governor, engine lag, droop and AGC (in the controller)", "Controlled Voltage Source ×3, Three-Phase Series RLC Branch"],
   ["Load, wind, PV base output", "Grid-following current injection synchronised to its own PLL (constant power) + 2 % resistive shunt", "Controlled Current Source ×3, Three-Phase Series RLC Branch (R)"],
   ["Measurements", "Bus voltage and the three branch currents", "Three-Phase V-I Measurement ×3, Mux, Unit Delay"],
   ["All control", "One MATLAB Function block calling vsgrl_emt_ctrl.m (VSG swing equation, limiter, diesel, PLL, EMS signals, feasibility layer, TD3 actor)", "MATLAB Function"],
   ["Solver", "Discrete, 100 µs (Specialized Power Systems)", "powergui"]],
  [2300, 4226, 2500]));

C.push(H2("B.2 Files you need"));
C.push(P("Unzip matlab_vsgrl_v5.zip (sent with this guide). It contains:"));
C.push(...TABLE(["File / folder", "Purpose"],
  [["export\\", "Data from Python: parameters (vsgrl_params.mat), trained TD3 actor (vsgrl_policy_val.mat), 12 test scenarios with their exact wind/load noise and the Python results (vsgrl_validation.mat)"],
   ["sim\\", "MATLAB version of the averaged (RMS) model, used as the reference"],
   ["simscape\\run_simscape_validation.m", "The script you run. Builds the model on the first run, simulates, compares, writes tables and figures"],
   ["simscape\\build_vsgrl_simscape.m", "Builds vsgrl_emt.slx automatically (called by the run script)"],
   ["simscape\\vsgrl_emt_ctrl.m", "All control code (inside the MATLAB Function block)"],
   ["simscape\\vsgrl_emt_params.m", "Computes every circuit and control parameter from the Python data (Part C)"],
   ["simscape\\vsgrl_emt_bench.m", "Same circuit without Simulink (cross-check; also used for the paper's current numbers)"],
   ["simscape\\diagnose_simscape.m", "Lists the Simscape blocks and parameters of your MATLAB if something fails"]],
  [3300, 5726]));

C.push(H2("B.3 First run (one scenario, about 5–10 minutes)"));
{ const S = STEP();
  C.push(S("Unzip matlab_vsgrl_v5.zip to a folder you can write to, for example C:\\Users\\ACER\\Documents\\. Do not use the MATLAB installation folder."));
  C.push(S("Close any open vsgrl_emt model in Simulink without saving, and delete an old vsgrl_emt.slx and slprj folder in the simscape folder if they exist (they come from earlier attempts)."));
  C.push(S("Start MATLAB R2021a and go to the simscape folder:"));
  C.push(...CODE("cd('C:\\Users\\ACER\\Documents\\matlab_vsgrl\\simscape')", "pwd          % must print the simscape folder"));
  C.push(S("Open run_simscape_validation.m and check lines 19–20:"));
  C.push(...CODE("SCENARIOS = 1;           % first run: one scenario", "USE_SIMULINK = true;     % use the Simscape model"));
  C.push(S("Run it:"));
  C.push(...CODE("run_simscape_validation"));
  C.push(S("Watch the Command Window. You should see, in this order:"));
  C.push(BUL("lines starting with \"using …\" (the library blocks it found), then \"Built …vsgrl_emt.slx\"; a Simulink window opens with the model;"));
  C.push(BUL("a pause of 1–2 minutes while the MATLAB Function block is compiled (first run only);"));
  C.push(BUL("the plausibility check after the first simulation:"));
  C.push(...CODE("Check (end of warm-up): bus voltage 0.998 pu (expect ~1), diesel 0.300 MW (expect 0.300),",
                 "  load injection 0.501 MW (reference 0.501), detected signs: current +1, injection +1"));
  C.push(BUL("three result lines, one per controller, and a figure comparing the RMS model (grey) with the Simscape model (dashed)."));
  C.push(S("Compare with the expected values below (from the script solver of the same circuit). Small differences (a few per cent) are normal, because Simscape solves the circuit with a different integration method; large differences mean something is wrong (Part D)."));
  C.push(...TABLE(["Scenario 1", "Nadir RMS / EMT (Hz)", "RoCoF 100 ms RMS / EMT (Hz/s)", "RMSE of Δf (Hz)"],
    [["fixed_tuned", "0.756 / 0.819", "2.27 / 4.47", "0.025"], ["fixed_feasible", "0.756 / 0.819", "2.27 / 4.47", "0.025"], ["policy (TD3)", "0.753 / 0.805", "2.28 / 4.47", "0.028"]],
    [2200, 2300, 2700, 1826])); }

C.push(H2("B.4 Full run (12 scenarios × 3 controllers)"));
{ const S = STEP();
  C.push(S("Change line 19 to SCENARIOS = 1:12; and run run_simscape_validation again. The model is already built and compiled, so it starts simulating at once. Expect roughly 1–3 minutes per simulation, 36 simulations in total; you can leave it running."));
  C.push(S("When it finishes, open the results folder (simscape\\results). Expected averages over the 12 scenarios:"));
  C.push(...TABLE(["Quantity (EMT vs RMS)", "Expected (script solver)", "Your Simscape result"],
    [["RMS difference of Δf", "0.014–0.018 Hz", ""], ["Worst-event nadir", "fixed: within 0.2 %; TD3: 4 % deeper", ""],
     ["BESS energy", "within 0.8 %", ""], ["RoCoF over 100 ms / 500 ms", "× 2.5 / +3 to +11 %", ""],
     ["Converter saturation time", "× 2.3–2.7", ""], ["Infeasible commitments, projected controllers", "≤ 0.03 s per episode", ""]],
    [3300, 3200, 2526]));
  C.push(S("Send simscape_summary.txt and simscape_scenario1.png to update the paper. If the values agree, the yellow note in Section VIII is replaced by \"confirmed in Simscape Electrical (MATLAB R2021a)\" and Table VII states the Simscape numbers.")); }
C.push(...TABLE(["Output file (simscape\\results)", "Content"],
  [["simscape_summary.txt", "Mean of every metric, RMS vs EMT, per controller (the numbers for Table VII)"],
   ["simscape_metrics.csv", "Every metric for every scenario and controller (opens in Excel)"],
   ["simscape_scenario<k>.png", "Frequency and VSG power, RMS vs EMT, for scenario k"],
   ["simscape_parity.png", "EMT against RMS for nadir, RoCoF (500 ms) and BESS energy"],
   ["emt_traces_sc<k>.mat", "Full EMT and RMS traces of scenario k (variable TR)"]],
  [3300, 5726]));

C.push(H2("B.5 Looking inside the model (optional)"));
{ const S = STEP();
  C.push(S("Open vsgrl_emt.slx. The sources are on the left (VSG_a/b/c, Diesel_a/b/c), the coupling impedances (Z_vsg, Z_diesel) and measurements (VI_vsg, VI_diesel, VI_load) in the middle, the load injection (Load_a/b/c) on the right, and the controller at the bottom."));
  C.push(S("Double-click Controller to see the code; it calls vsgrl_emt_ctrl.m, which you can open and read (every line is commented)."));
  C.push(S("After a run, the logged signals are in the variable emt_mon (one row every 10 ms, 22 columns). For example, to plot frequency and VSG power of the last simulation:"));
  C.push(...CODE("out = sim('vsgrl_emt');  m = out.get('emt_mon');",
                 "subplot(2,1,1); plot(m(:,1), m(:,2)); ylabel('\\Deltaf (Hz)'); grid on",
                 "subplot(2,1,2); plot(m(:,1), m(:,4)); ylabel('P_{VSG} (MW)'); xlabel('t (s)'); grid on"));
  C.push(S("Columns of emt_mon: 1 time (s), 2 Δf (Hz), 3 RoCoF (Hz/s), 4 VSG power (MW), 5 BESS power (MW), 6 diesel mechanical power (MW), 7 SoC, 8 J (s), 9 D (pu), 10 α, 11 P_set (MW), 12 headroom (MW), 13 saturation (MW), 14 bus voltage (pu), 15 VSG reactive power (Mvar), 16 diesel electrical power (MW), 17 load injection measured (MW), 18 load injection reference (MW), 19–20 detected signs, 21 PLL Δf raw (Hz), 22 diesel rotor Δf (Hz).")); }

// ====================================================================== PART C
C.push(H1("Part C. Parameters: Python and Simscape"));
C.push(P("All parameters come from configs/default.yaml of the Python code. They are exported to export\\vsgrl_params.mat (field names are the YAML keys joined with underscores) and converted by vsgrl_emt_params.m. Nothing is typed by hand in Simulink."));
C.push(H2("C.1 Electrical network (derived)"));
C.push(...TABLE(["Quantity", "Value", "How it is obtained"],
  [["Line-to-line voltage, base power", "400 V, 2 MVA", "chosen for the EMT model; Z_base = V²/S = 0.08 Ω"],
   ["EMT time step; warm-up; episode", "100 µs; 0.5 s; 30 s", "Ts, Tw, env.episode_s"],
   ["VSG coupling reactance X_v", "0.5 pu → L_v = 127.3 µH, R_v = 4 mΩ", "X_v = 1/K_s (K_s = system.vsg.sync_coeff_pu = 2.0), X/R = 10"],
   ["Diesel reactance X_d", "1.25 pu → L_d = 318.3 µH, R_d = 10 mΩ", "X_d = 1/K_d (K_d = system.diesel.sync_coeff_pu = 0.8), X/R = 10"],
   ["Shunt resistance", "4 Ω per phase (2 % load)", "R_sh = V²/(0.02·S); also avoids an all-inductive node"],
   ["Initial EMFs (scenario 1)", "E_v0 = 1.008 pu ∠3.4°; E_d0 = 1.036 pu ∠10.4°", "E = 1 + (R + jX)·P0 for 1 pu bus voltage, unity power factor"],
   ["PLL", "20 Hz bandwidth: Kp = 175.9, Ki = 15 791", "Kp = 2·0.7·ω_n, Ki = ω_n², ω_n = 2π·20"],
   ["Converter power limiter", "K_lim = 100 rad/s per pu", "drives the VSG power back inside its limits within ~5 ms"],
   ["VSG voltage control", "Ki_v = 10 pu/s per pu", "slow integral on the bus voltage"]],
  [2600, 2900, 3526]));
C.push(H2("C.2 Plant parameters (from the Python configuration)"));
C.push(...TABLE(["Parameter", "Python key (configs/default.yaml)", "Value"],
  [["Frequency; system base", "system.f_nominal_hz; system.s_base_mva", "50 Hz; 2 MVA"],
   ["Diesel rating; inertia; damping", "system.diesel.rated_mw; inertia_h_s; damping_pu", "0.5 MW; 2 s (own base) = 0.5 s (system base); 2 pu"],
   ["Diesel droop; governor; engine; ramp", "system.diesel.droop; governor_time_s; engine_time_s; ramp_pu_per_s", "5 %; 0.2 s; 0.5 s; 1 pu/s"],
   ["Diesel AGC / BESS secondary gain", "system.diesel.secondary_ki; system.bess.secondary_ki", "2.0; 2.0"],
   ["BESS power; energy", "system.bess.power_mw; energy_mwh", "0.5 MW; 2 MWh"],
   ["SoC window; taper; efficiencies", "system.bess.soc_min / soc_max; soc_taper; eta_charge / eta_discharge", "0.10–0.95; 0.05; 0.95 / 0.95"],
   ["PV rating; de-loading; release lag", "system.pv.rated_mw; deload_fraction; response_time_s", "0.8 MW; 15 %; 80 ms"],
   ["Wind rating; cut-in / rated / cut-out", "system.wind.rated_mw; cut_in_ms; rated_speed_ms; cut_out_ms", "1.0 MW; 2.5 / 10 / 25 m/s"],
   ["Wind turbulence; rotor smoothing", "system.wind.turbulence_intensity; rotor_smoothing_s", "10 %; 0.5 s"],
   ["Load damping; load noise", "system.load.damping_pu; noise_frac", "1 pu; 0.5 %"],
   ["Frequency filter", "system.vsg.measurement_filter_s", "20 ms"],
   ["VSG parameter ranges", "system.vsg.h_min_s / h_max_s; d_min_pu / d_max_pu", "J 0.2–8 s; D 0–50 pu"],
   ["EMS", "system.ems.diesel_target_frac; max_dispatch_frac", "60 %; 80 %"]],
  [2700, 3900, 2426]));
C.push(H2("C.3 Control and feasibility parameters"));
C.push(...TABLE(["Parameter", "Python key", "Value"],
  [["Decision interval", "env.agent_dt_s", "50 ms"],
   ["Rate limiter", "env.param_filter_s", "0.25 s"],
   ["Feasibility constraint", "env.headroom_constraint; env.projection", "on; band_power (max rule, clipping)"],
   ["Band and RoCoF limit of the projection", "env.reward.f_band_hz; system.grid_code.rocof_limit_hz_s", "0.2 Hz; 1 Hz/s"],
   ["Tuned fixed VSG (base of the residual agent)", "eval.baseline_params.fixed_tuned", "J = 3 s, D = 15 pu, α = 1.0"],
   ["TD3 actor", "export\\vsgrl_policy_val.mat", "16 → 256 → 256 → 3, seed 1, final checkpoint"]],
  [3000, 3800, 2226]));
C.push(H2("C.4 Scenario parameters (example: test scenario 1)"));
C.push(P("These change with every scenario and are computed by the same EMS dispatch as in Python (vsgrl_reset.m):"));
C.push(...TABLE(["Quantity", "Scenario 1"],
  [["Load at the hour", "0.764 MW"], ["Diesel dispatch P_d0", "0.300 MW"], ["BESS dispatch P_b0", "0.241 MW"],
   ["PV base output / reserve", "0.223 MW / 0.039 MW"], ["Wind", "0 MW (below cut-in)"], ["Initial SoC", "0.473"],
   ["Load events", "+0.365 MW at 0.80 s, −0.331 MW at 20.80 s"]],
  [4500, 4526]));

// ====================================================================== PART D
C.push(H1("Part D. If something goes wrong"));
C.push(...TABLE(["Message or symptom", "Cause", "What to do"],
  [["The current directory '…\\matlab\\bin' is reserved", "MATLAB's current folder is its installation folder", "cd into the simscape folder (Step B.3.3); the latest run script does this itself"],
   ["Block \"…\" not found", "library differs in your release", "run diagnose_simscape and send the output"],
   ["Could not set \"…\" on … Available parameters: …", "a block parameter has another name in R2021a", "send the full message (it lists the correct names)"],
   ["Could not connect … to …", "a wiring step failed", "send the full message"],
   ["Error in the MATLAB Function block / code generation", "a statement in vsgrl_emt_ctrl.m is not supported by code generation", "send the message; if MATLAB asks for a C compiler, run mex -setup"],
   ["Bus voltage far from 1 pu, or diesel power far from expected in the check line", "a polarity or unit setting of a block", "send the check line and a screenshot of the model"],
   ["Simulation very slow (> 10 min per run)", "the model runs in Normal mode on a slow laptop", "leave it running; or set SCENARIOS to fewer scenarios"],
   ["Empty Simulink window after the build stops", "the build failed before adding blocks", "close it without saving and read the red text in the Command Window"]],
  [3000, 2900, 3126]));
C.push(P({ t: "When you send an error, copy the complete red text from the Command Window. Every error message of the build script names the step and the block involved, so it can usually be fixed in one round.", i: true }));

const doc = new Document({
  creator: "solar-wind-rl-estimation", title: "IREA next steps and Simscape guide",
  styles: { default: { document: { run: { font: FONT, size: 22 } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1080, hanging: 300 } } } }] },
    ...lists.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 500, hanging: 360 } } } }] }))] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } }, children: C }],
});
Packer.toBuffer(doc).then((buf) => { const out = path.join(__dirname, "IREA_next_steps_and_Simscape_guide.docx"); fs.writeFileSync(out, buf); console.log("wrote", out); });
