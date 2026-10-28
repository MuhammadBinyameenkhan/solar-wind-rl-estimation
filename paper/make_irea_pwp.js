// IREA manuscript in the Praise Worthy Prize (PWP) template, as used for the authors' IREMOS manuscript.
// Run: node paper/make_irea_pwp.js  ->  paper/IREA_manuscript_PWP.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  ShadingType, BorderStyle, LevelFormat, SectionType, TabStopType,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const FIG = (f) => path.join(ROOT, "results", "figures", f);
const FONT = "Times New Roman";
const BODY = 20;                       // 10 pt
const FULL_W = 9639;                   // 11906 − 1417 − 850
const COL_W = 4536;                    // (9639 − 567) / 2

function runs(parts, size = BODY, italic = false) {
  return parts.map((p) => {
    if (typeof p === "string") return new TextRun({ text: p, font: FONT, size, italics: italic });
    return new TextRun({ text: p.t, bold: !!p.b, italics: p.i !== undefined ? !!p.i : italic, font: FONT, size: p.size || size,
      superScript: !!p.sup, subScript: !!p.sub,
      shading: p.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined });
  });
}
const TODO = (t) => ({ t: `[AUTHOR: ${t}]`, hl: true });
const P = (...parts) => {
  // keep the old "small italic note" usage: P({t, size: 17, i: true}) -> TableNote style
  if (parts.length === 1 && typeof parts[0] === "object" && parts[0].size === 17)
    return new Paragraph({ spacing: { before: 40, after: 160 }, children: runs([{ ...parts[0], size: 16 }]) });
  return new Paragraph({ children: runs(parts), alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 227 } });
};
let SEC = "", sub = 0;
const H1 = (t) => {
  const m = t.match(/^([IVX]+)\.\s/); SEC = m ? m[1] : ""; sub = 0;
  return new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 360, after: 120 },
    children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })] });
};
const H2 = (t) => {
  sub += 1;
  const title = t.replace(/^[A-Z]\.\s+/, "");
  return new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 360, after: 120 },
    children: [new TextRun({ text: `${SEC}.${sub}. ${title}`, font: FONT, size: BODY, italics: true })] });
};
const EQ = (txt, n) => new Paragraph({ spacing: { before: 80, after: 80 },
  tabStops: [{ type: TabStopType.CENTER, position: 2268 }, { type: TabStopType.RIGHT, position: COL_W }],
  children: [new TextRun({ text: "\t" + txt, font: FONT, size: 18, italics: true }), new TextRun({ text: `\t(${n})`, font: FONT, size: BODY })] });
const BUL = (...parts) => new Paragraph({ children: runs(parts), numbering: { reference: "bul", level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 } });
const roman = (n) => ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"][n - 1];
let tabN = 0;
// wide blocks (figures and tables) are placed in one-column sections, as in the IREMOS manuscript
function FIGURE(file, _w, _h, widthIn, caption) {
  const p = file.startsWith("..") ? path.join(ROOT, "results", "figures", file) : FIG(file);
  const buf = fs.readFileSync(p);
  const wpx = buf.readUInt32BE(16), hpx = buf.readUInt32BE(20);
  const w = Math.round(Math.min(widthIn, 6.4) * 96), h = Math.round(w * hpx / wpx);
  return [{ wide: [
    new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h },
        altText: { title: caption.slice(0, 40), description: caption, name: path.basename(p) } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 60, after: 200 }, children: runs([caption], 16) }),
  ] }];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(caption, header, rows, widths) {
  tabN += 1;
  const tot = widths.reduce((a, b) => a + b, 0);
  const scale = Math.min(1, FULL_W / tot);
  const ws = widths.map((w) => Math.floor(w * scale));
  const title = caption.replace(/^TABLE\s+[IVX]+\.\s*/, "").toUpperCase();
  const cell = (txt, j, head) => new TableCell({ borders, width: { size: ws[j], type: WidthType.DXA },
    margins: { top: 30, bottom: 30, left: 60, right: 60 },
    children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: String(txt), font: FONT, size: 16, bold: head })] })] });
  return [{ wide: [
    new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: `TABLE ${roman(tabN)}`, font: FONT, size: 16 }), new TextRun({ text: title, font: FONT, size: 16, break: 1 })] }),
    new Table({ width: { size: ws.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: ws,
      rows: [header, ...rows].map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true, children: r.map((c, j) => cell(c, j, i === 0)) })) }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ] }];
}
const EMT = JSON.parse(fs.readFileSync(path.join(__dirname, "emt_numbers.json"), "utf8"));
const SUP = (t) => ({ t, sup: true });

// ---------- title block (one column) ----------
const CHECKLIST = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: runs([{ t: "CHECKLIST OF MISSING ITEMS (delete this box before submission)", b: true, hl: true }], 22) }),
  ...["Confirm the author list, order and affiliations; confirm the corresponding-author details.",
      "Insert the author photographs before each biography (Authors’ information), as in the IREMOS manuscript.",
      "Replace the synthetic load profile by a measured Thai load profile if one is available (Section IV), or keep the statement as a limitation.",
      "Update the status of references [15] (TREC) and [16] (IREMOS).",
      "Add the public GitHub URL or Zenodo DOI (Data and Code Availability).",
      "Confirm the funding statement (Acknowledgements).",
      "Check the year, volume and pages of every reference against its DOI.",
      "Check the IREA author guidelines for the page limit, figure resolution and reference style before submission."].map((t, i) =>
    new Paragraph({ spacing: { after: 60 }, indent: { left: 340, hanging: 340 }, children: runs([{ t: `${i + 1}. ${t}`, hl: true }], 18) })),
  new Paragraph({ spacing: { after: 400 }, children: [] }),
];
const HEAD = [...CHECKLIST,
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ font: FONT, size: 32,
    text: "Bounding the Benefit of Learned Virtual-Inertia Scheduling in a Hybrid Diesel–PV–Wind–BESS Microgrid: Oracle Analysis, Headroom Projection and Circuit-Level Validation" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: runs([
    "Muhammad Binyameen Khan", SUP("1"), ", Padej Pao-La-Or", SUP("1"), ", Arthit Srikaew", SUP("1"), ", Tosaphol Ratniyomchai", SUP("1"),
    ", Jirawadee Polprasert", SUP("2"), ", Anant Oonsivilai", SUP("1"), " ", TODO("confirm author list and order")], 24) }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 850, right: 850 }, spacing: { after: 200 }, children: [
    new TextRun({ text: "Abstract – ", bold: true, font: FONT, size: BODY }),
    new TextRun({ font: FONT, size: BODY, italics: true, text: "Reinforcement learning is increasingly proposed for scheduling the virtual inertia and damping of grid-forming battery converters, yet the benefit of such scheduling in a particular microgrid is seldom bounded before agents are trained. This paper bounds it for an isolated 2 MVA microgrid in which a 0.5 MW diesel generator is the only source of physical inertia and a 0.5 MW / 2 MWh battery, with a de-loaded 0.8 MW photovoltaic plant, supplies synthetic inertia through a virtual synchronous generator; a 1 MW wind turbine completes the system. Operating points are derived from one year of hourly ERA5 wind and NASA POWER solar data for Nakhon Ratchasima, Thailand. A per-scenario oracle shows that adapting the virtual inertia and damping can improve the control objective by at most 2.1 % over the best fixed setting. A direction-aware headroom projection, which sizes the damping and inertial commitments at the instants their power peaks, cuts the time a learned TD3 policy spends on undeliverable commitments from 5.07 s to 0.02 s per 30 s episode, and scaling both parameters by one factor reduces converter saturation further than clipping each. Residual TD3 and DDPG agents (5 seeds × 1000 episodes) do not exceed a validation-tuned fixed setting on the overall objective. A three-phase electromagnetic-transient model reproduces the averaged-model frequency trajectories within " + EMT.rmse_range + " Hz RMS and shows that phase jumps at load steps raise the 100 ms rate of change of frequency measured by a phase-locked loop by a factor of about " + EMT.rocof100_factor + "." })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 850, right: 850 }, spacing: { after: 360 }, children: [
    new TextRun({ text: "Keywords: ", bold: true, font: FONT, size: BODY }),
    new TextRun({ italics: true, font: FONT, size: BODY, text: "Converter Headroom, Hybrid Microgrid, Reinforcement Learning, Synthetic Inertia, Virtual Synchronous Generator" })] }),
];
const C = [];
// ===== I. INTRODUCTION =====
C.push(H1("I. Introduction"));
C.push(P("Small isolated power systems are moving from diesel-only supply to hybrid plants in which photovoltaic (PV) and wind generation, connected through power converters, cover a growing share of the load [1], [2]. The diesel units that remain still set the rotational inertia, and when they run at part load the rate of change of frequency (RoCoF) and the frequency nadir after a load step become critical. A battery energy storage system (BESS) whose converter is controlled as a virtual synchronous generator (VSG) can add synthetic inertia and damping [3], [4], and because these are software parameters it is natural to adapt them online, by rules [5]–[8] or by deep reinforcement learning (RL) [9]–[14]."));
C.push(P("In two earlier studies the authors examined adaptive VSG control for a microgrid without any synchronous machine [15], [16]. They introduced a converter-headroom requirement that charges every declared pair of inertia and damping with the power it implies at the grid-code limits, derated both parameters proportionally when that power was not available, and found, under a ten-seed protocol with tuned baselines, that learned controllers mainly trade regulation against reserved headroom rather than dominating a well-tuned constant controller [16]. Those findings leave four questions open, and this paper addresses them:"));
C.push(BUL({ t: "Physical inertia. ", b: true }, "What changes when a synchronous machine shares the transient with the VSG, so that part of every step is taken by the diesel rotor and the VSG power depends on the electrical coupling between the two machines?"));
C.push(BUL({ t: "Size of the prize. ", b: true }, "Can the benefit of adaptive scheduling be bounded before any agent is trained, so that the effort of training is spent only where it can pay off?"));
C.push(BUL({ t: "Form of the requirement. ", b: true }, "Is the summed requirement, which assumes that the largest RoCoF and the largest deviation occur together, unnecessarily conservative, and is proportional derating better or worse than clipping each parameter?"));
C.push(BUL({ t: "Model fidelity. ", b: true }, "Do conclusions drawn from an averaged frequency model survive in a three-phase circuit with a phase-locked loop (PLL) and a converter power limiter?"));
C.push(P("The contributions are: (i) a two-machine model of a diesel–VSG microgrid with a de-loaded PV reserve, state-of-charge (SoC) dependent BESS limits, an energy management system (EMS) and secondary control, driven by a full year of site data; (ii) a per-scenario oracle that bounds the gain of any scheduler of the VSG parameters; (iii) a direction-aware, time-separated headroom projection and an ablation that compares it with the summed requirement of [15], [16] and compares clipping with proportional derating; (iv) an evaluation of residual TD3 and DDPG agents, including what the projection prevents in the learned policy; and (v) a two-stage validation, an independent MATLAB re-implementation and a three-phase electromagnetic-transient (EMT) model. Table I summarises how this study differs from [15], [16]."));
C.push(...TABLE("TABLE I. Scope of this study compared with the authors' earlier work",
  ["Aspect", "Earlier studies [15], [16]", "This study"],
  [["Plant", "Fully converter-interfaced; single swing equation with a residual inertia of 0.5 s", "Diesel SG + grid-forming VSG coupled through synchronising coefficients; de-loaded PV; SoC-dependent BESS; EMS; secondary control"],
   ["Weather input", "Site-calibrated scenarios [15]; 1 Hz measured records from three days [16]", "One year (2024) of hourly ERA5 and NASA POWER data at the study site"],
   ["Research question", "DDPG vs TD3 vs fixed and tuned controllers", "Upper bound on the gain of adaptation (oracle), before training"],
   ["Headroom requirement", "Sum of inertial and damping power at the limits; proportional derating", "Direction-aware, time-separated (max) requirement; clipping and proportional derating compared"],
   ["Learner", "Absolute actions (J, D, K_q)", "Residual actions around a tuned VSG (J, D, PV share α); projection ablated in the learned policy"],
   ["Validation", "Averaged model", "MATLAB re-implementation and three-phase EMT model"]],
  [1700, 3500, 3826]));

// ===== II. RELATED WORK =====
C.push(H1("II. Related Work"));
C.push(P("The synchronverter reproduces the machine equations inside the converter controller [3], and VSG variants are reviewed in [4]. Rule-based schemes alternate the inertia according to the direction of the rotor swing [5], adapt inertia and damping together [6], [7] or respect SoC limits [8]. Learning-based schemes tune droop, inertia and damping with DDPG [9], soft actor–critic [10] or TD3 [11], [12], including real-time simulator validation [12], and recent comparisons cover several algorithms and benchmark controllers [13], [14]; a broader review of RL in power-system control is given in [31]. Converter current limiting bounds what a grid-forming controller can deliver [29], [30], but most adaptive formulations bound the parameters only by fixed ranges. The studies in [15], [16] add a headroom requirement for converter-only microgrids; none of the cited works bounds the achievable gain of adaptation in advance or validates a learned VSG schedule in a circuit-level model of a hybrid diesel–VSG system."));

// ===== III. SYSTEM =====
C.push(H1("III. Hybrid Microgrid Model"));
C.push(P("The test system (Fig. 1, Table II) is an isolated 50 Hz microgrid on a 2 MVA base. A 0.5 MW diesel synchronous generator (SG) with an inertia constant of 2 s on its own rating provides the only physical inertia, 0.5 s on the system base. A 0.5 MW / 2 MWh BESS is connected through a grid-forming converter controlled as a VSG; a 0.8 MW PV plant is operated 15 % below its maximum power point, so that this margin can be released as fast reserve; and a 1.0 MW IEC class III wind turbine and the load are represented as grid-following injections."));
C.push(...FIGURE("../../paper/proposal_figs/fig_single_line.png", 0, 0, 5.6, "Fig. 1. Hybrid microgrid and control structure."));
C.push(...TABLE("TABLE II. Plant parameters",
  ["Component", "Parameter", "Value"],
  [["System", "Base power; frequency", "2.0 MVA; 50 Hz"],
   ["Diesel SG", "Rating; H_d (own base); droop; governor / engine lag", "0.5 MW; 2 s; 5 %; 0.2 s / 0.5 s"],
   ["BESS + VSG", "Power; energy; SoC window; efficiency", "0.5 MW; 2 MWh; 0.10–0.95; 0.95 each way"],
   ["PV plant", "Rating; de-loading d; release lag", "0.8 MW; 15 %; 80 ms"],
   ["Wind turbine", "Rating; cut-in / rated speed; hub height", "1.0 MW; 2.5 / 10 m/s; 100 m"],
   ["Coupling", "Synchronising coefficients K_d, K_s", "0.8 pu; 2.0 pu"],
   ["Secondary control", "Integral gain (diesel AGC, BESS set-point)", "2.0 pu/(pu·s)"],
   ["VSG parameters", "J_v; D_v; PV share α", "0.2–8 s; 0–50 pu; 0–1"],
   ["Load and events", "Load range; load damping; steps per 30 s", "0.3–0.8 MW; 1 pu; 2–3 of 0.2–0.4 MW"]],
  [1900, 3726, 3400]));
C.push(H2("A. Two-machine dynamics"));
C.push(P("The SG and the VSG are voltage sources behind reactances that meet at the load bus. Linearised around the operating point, the network shares a net imbalance ΔP_net between the two machines in proportion to their synchronising coefficients, and the bus frequency is the coefficient-weighted mean of their speeds:"));
C.push(EQ("P_v = K_s (K_d δ + ΔP_net) / (K_d + K_s),     ΔP_net = ΔP_L − ΔP_w + D_L P_L0 Δω_b", 1));
C.push(EQ("Δω_b = (K_d Δω_d + K_s Δω_v) / (K_d + K_s)", 2));
C.push(P("where δ is the angle of the virtual rotor relative to the SG rotor. The rotors obey [24]"));
C.push(EQ("2H_d dΔω_d/dt = ΔP_m − ΔP_e,d − D_d (Δω_d − Δω_b)", 3));
C.push(EQ("2J_v dΔω_v/dt = P_set − P_v − D_v Δω_v,     dδ/dt = ω_0 (Δω_v − Δω_d)", 4));
C.push(P("so that, at the instant of a step, the VSG takes K_s/(K_s + K_d) ≈ 71 % of it whatever J_v and D_v are; the virtual inertia J_v and damping D_v shape only how the shared transient evolves. ΔP_m follows a droop governor with automatic generation control, and P_set is moved by an integral BESS secondary control. The VSG power is limited to the band that the BESS and PV can deliver,"));
C.push(EQ("−(P_ch,max(SoC) + P_b0) + P_pv,s ≤ P_v ≤ P_dis,max(SoC) − P_b0 + P_pv,s", 5));
C.push(P("where P_b0 is the BESS power dispatched by the EMS, the SoC-dependent limits taper linearly within 5 % of the SoC bounds, and P_pv,s = α P_v is the PV share of the support, released with an 80 ms lag within the de-loading margin. When the limit is reached, an anti-windup holds the virtual rotor at the SG speed. The model is integrated at 2 ms with a symplectic Euler scheme, and frequency is measured through a 20 ms filter representing the PLL."));
C.push(H2("B. Energy management"));
C.push(P("A rule-based EMS sets the operating point of each hour: renewable surplus first charges the BESS and is curtailed only when the BESS limit is reached, and a deficit is met by discharging the BESS (up to 80 % of its SoC-dependent limit) so that the diesel unit stays near 60 % of its rating. This dispatch consumes part of the converter capability that synthetic inertia needs, most noticeably during the evening peak, which is why the headroom available to the VSG varies widely over the year. Operating points at which load would have to be shed, or at which the largest cumulative load increase would exceed the diesel spare capacity plus the VSG headroom, are screened out (7.4 % of test draws)."));

// ===== IV. DATA =====
C.push(H1("IV. Site Data"));
C.push(P("In [16] the frequency excursions were set mainly by the load steps, while the weather acted through the operating point and therefore through the available headroom. This study therefore samples operating points across a whole year rather than resolving sub-hourly weather. Hourly 100 m wind components come from ERA5 [20] on a 2 × 2 grid around the site (14.98° N, 102.10° E, 226 m) and are interpolated bilinearly; hourly global horizontal irradiance and temperature come from NASA POWER [21] and are converted from local solar time to UTC. Air density is computed from the NASA POWER temperature and the pressure at the site elevation. The two sources overlap for 8777 h of 2024 (Fig. 2). The site is a low-wind site (ERA5 mean 4.2 m/s at 100 m), so a class III turbine is used [22], giving a capacity factor of 9.5 %; the PV capacity factor is 17.3 %. Within each hour, wind turbulence (intensity 10 %) and load noise (0.5 %) are added."));
C.push(P("With a single year, a chronological split would place each season in only one subset. The data are therefore divided into weekly blocks, five for training, one for validation and one for testing in every seven weeks, so that all seasons appear in every subset and whole weeks separate them (Table III). The load is a synthetic daily, weekly and seasonal profile between 0.3 and 0.8 MW. ", TODO("replace with a measured load profile if one is available")));
C.push(...TABLE("TABLE III. Operating-point data (2024) by subset",
  ["Subset", "Hours", "Hub wind (m/s)", "Wind CF", "PV CF", "GHI (W/m²)", "Load (MW)", "RES share"],
  [["All", "8777", "4.19", "9.5 %", "17.3 %", "213", "0.64", "36 %"],
   ["Training", "6425", "4.38", "10.5 %", "17.2 %", "212", "0.64", "37 %"],
   ["Validation", "1176", "3.71", "7.7 %", "17.1 %", "211", "0.64", "33 %"],
   ["Test", "1176", "3.67", "6.3 %", "18.1 %", "223", "0.64", "32 %"]],
  [1226, 900, 1150, 1000, 1000, 1150, 1250, 1350]));
C.push(...FIGURE("fig_data_overview.png", 0, 0, 6.0, "Fig. 2. Daily means of the hourly operating points; validation and test weeks shaded."));

// ===== V. HEADROOM =====
C.push(H1("V. Feasible Synthetic Inertia"));
C.push(H2("A. Direction-aware headroom"));
C.push(P("The reserve the VSG can deliver depends on the direction of the event. While the frequency is at or below nominal, the upward headroom applies, and during an over-frequency event the downward headroom:"));
C.push(EQ("h_up = max(P_dis,max(SoC) − P_b0, 0) + d·P_MPP,     h_dn = max(P_ch,max(SoC) + P_b0, 0) + P_pv,0", 6));
C.push(P("A BESS that the EMS is already discharging therefore has little upward but much downward headroom, and the PV margin adds to the upward headroom only."));
C.push(H2("B. Summed versus time-separated requirement"));
C.push(P("A pair (J_v, D_v) commits inertial power 2J_v·RoCoF and damping power D_v·Δf. The requirement used in [15], [16] adds both at their limits,"));
C.push(EQ("h_req,sum = 2J_v·RoCoF_lim + D_v·Δf_lim", 7));
C.push(P("which assumes that the largest RoCoF and the largest deviation occur at the same instant. In a swing response they do not: the RoCoF peaks immediately after the step, while the deviation is still close to zero, and the deviation peaks at the nadir, where the RoCoF is zero. Each mechanism must therefore be deliverable at its own peak, which gives the time-separated requirement"));
C.push(EQ("h_req,max = max(2J_v·RoCoF_lim, D_v·Δf_band)", 8));
C.push(P("with Δf_band = 0.2 Hz, the maximum steady-state frequency deviation of [23], and RoCoF_lim = 1 Hz/s. Whether (8) is safe in practice, given that both terms are partly active between the two peaks, is checked below through the converter saturation it produces."));
C.push(H2("C. Derating"));
C.push(P("When the requirement exceeds h, the commanded pair must be reduced. It can be clipped parameter by parameter, J_v ≤ h/(2RoCoF_lim) and D_v ≤ h/Δf_band, which keeps whichever parameter is already feasible; or both parameters can be scaled by one factor, as in [16],"));
C.push(EQ("(J_v, D_v) ← (J_v, D_v)·min(1, h / h_req)", 9));
C.push(P("which preserves their ratio. In every variant the commanded parameters first pass a 0.25 s rate limiter and are then derated, so that feasibility takes precedence over smoothness. An infeasible commitment is any instant at which the applied pair violates the requirement; its duration per 30 s episode measures what the derating prevents. The RL agents in Section VI use the time-separated requirement with clipping; Section VII.2 compares all variants."));

// ===== VI. METHODS =====
C.push(H1("VI. Scheduling Problem and Evaluation"));
C.push(H2("A. Episodes and objective"));
C.push(P("An episode lasts 30 s from a sampled hourly operating point and contains two or three load steps of 0.2–0.4 MW (three quarters of them increases), at least 7 s apart, with the cumulative change limited to ±0.4 MW; the SoC, the AGC state and the BESS set-point carry over between events. The parameters (J_v, D_v, α) are updated every 50 ms. The cost of each interval penalises the frequency only outside ±0.2 Hz and the RoCoF only above 1 Hz/s, together with the fast VSG power above its set-point (the response that J_v and D_v control), the BESS power, converter saturation and protection-limit violations:"));
C.push(EQ("c = w_f⟨(|Δf|−0.2)₊²⟩/0.5² + w_in⟨Δf²⟩/0.5² + w_r⟨(|RoCoF|−1)₊²⟩ + w_fast⟨(P_v−P_set)²⟩/P_b,max² + w_b⟨ΔP_bess²⟩/P_b,max² + w_s⟨sat⟩/0.05 + w_v·viol", 10));
C.push(P("with (w_f, w_in, w_r, w_fast, w_b, w_s, w_v) = (1, 0.02, 0.5, 2, 0.1, 2, 1), and the objective return is −Σc. The weights were chosen so that the best fixed setting has an interior damping; with a plain quadratic frequency penalty, maximum damping was always best and the scheduling problem became trivial. Because the conclusions of Section VII should not hinge on these weights, the learned policies are also compared with the fixed settings by multi-objective dominance, which does not use them."));
C.push(H2("B. Oracle bound"));
C.push(P("Before training, a grid of 24 fixed settings (J_v ∈ {1, 3, 5, 8} s, D_v ∈ {5, 10, 15, 20, 30, 50} pu) is simulated on 40 validation scenarios. The best single setting is compared with an oracle that picks the best setting separately for each scenario, that is, a scheduler that knows the operating point and the coming events. Because a fixed setting per scenario is a restricted schedule, the oracle bounds the gain of scenario-level adaptation; within-episode switching can add to it, which the learned agents test directly."));
C.push(H2("C. Residual agents"));
C.push(P("The agents observe 16 normalised quantities (frequency deviation and RoCoF, VSG power, virtual-rotor slip, upward, downward and PV headroom, SoC, wind, PV and diesel power, diesel spare capacity, the operating-point load, and the currently applied J_v, D_v and α) and output a ∈ [−1, 1]³. The action is residual [19]: a = 0 reproduces the validation-tuned fixed setting, and a = ±1 moves each parameter to its projected bound. The output layer of the actor is initialised to zero, so the untrained agent is exactly the tuned controller. TD3 [17] and DDPG [18] share networks (two hidden layers of 256 units), learning rates (10", SUP("−4"), " actor, 3×10", SUP("−4"), " critic), discount 0.99, exploration (Gaussian, 0.10 → 0.03) and budget (1000 episodes × 600 decisions × 5 seeds); the best checkpoint on 20 validation scenarios is retained, with the untrained agent included as a candidate. An action-rate penalty and a penalty on ‖a‖² are used in training only and are not part of the reported return. A third configuration, TD3 trained and tested without the projection, isolates its effect."));
C.push(H2("D. Benchmarks and statistics"));
C.push(P("The benchmarks are diesel only, grid-following BESS droop, a standard VSG (J_v = 3 s, D_v = 20 pu), a bang-bang alternating-inertia VSG [5] and the validation-tuned fixed VSG (J_v = 3 s, D_v = 15 pu, α = 1.0), with and without the projection. All controllers are evaluated on the same 200 test scenarios. The metrics are the worst-event nadir, the largest RoCoF over 100 ms, BESS energy throughput, converter saturation time, infeasible-commitment time and the objective return. Learned controllers are averaged over seeds per scenario, and paired differences are tested with the Wilcoxon signed-rank test [25] with Holm correction [26]; several seeds are used as recommended in [27], [28]."));

// ===== VII. RESULTS =====
C.push(H1("VII. Results"));
C.push(H2("A. The size of the prize"));
C.push(P("On the 40 validation scenarios the best fixed setting (J_v = 3 s, D_v = 15 pu) reaches an objective return of −94.66 and the oracle −92.66, a margin of 2.0 points or 2.1 %. The damping chosen by the oracle hardly depends on the headroom (12–15 pu from the lowest to the highest headroom tercile), because 15 pu requires only about 0.12 MW at the band edge, which even the tightest operating points can supply. The margin is small for two reasons that are specific to a hybrid system: the coupling of (1) gives the VSG about 71 % of every step regardless of its parameters, and secondary control restores the frequency within 10–20 s, so that J_v and D_v act only on a short part of each event."));
C.push(H2("B. Which feasibility rule?"));
C.push(P("Table IV and Fig. 3 apply each rule to five fixed settings on the 200 test scenarios, from the tuned setting to the largest one the ranges allow; the low (1 s, 10 pu) and high (4 s, 30 pu) settings are those used in [15], [16]. Without any constraint, the high setting needs more headroom than is available for 5.3 s and the largest setting for 17.6 s of every 30 s episode under (8), confirming in a system with physical inertia that literature-style gains are frequently undeliverable. Proportional derating (9) lowers the converter saturation compared with clipping for every setting (paired Wilcoxon, p < 10", SUP("−4"), ") and raises the return for every setting except the tuned one (+1.4, +2.0 and +8.8 for the standard, high and largest settings, p < 10", SUP("−3"), "). The summed requirement (7) is more conservative than (8): it lowers saturation and BESS energy further but deepens the nadir by 0.016 Hz for the tuned setting and by 0.04–0.08 Hz for the high-gain settings. With the wider limits of [16] (0.5 Hz, 2 Hz/s), every setting is reduced to about J_v ≈ 2 s and D_v ≈ 11–15 pu, so higher declared gains no longer change the response, and the return drops to between −119 and −123, compared with −106 for the tuned setting under (8). For the tuned setting, all rules based on the limits of this study change the return by less than one point: the rule matters for aggressive commands, which are exactly what an unconstrained learner tends to issue (Section VII.4)."));
C.push(...TABLE("TABLE IV. Feasibility rules applied to fixed settings (means over 200 test scenarios)",
  ["Setting (J_v, D_v)", "Rule", "Saturation (s)", "Nadir (Hz)", "BESS (kWh)", "Infeasible (s)*", "Return"],
  [["Tuned (3, 15)", "None", "0.103", "0.573", "0.775", "2.330", "−105.9"],
   ["", "Max, clip", "0.123", "0.573", "0.775", "0.007", "−106.1"],
   ["", "Max, scale", "0.097", "0.574", "0.772", "0.008", "−105.1"],
   ["", "Sum, scale", "0.090", "0.589", "0.764", "0.008", "−105.7"],
   ["", "Sum, scale, wide", "0.073", "0.783", "0.702", "0.011", "−123.1"],
   ["High (4, 30)", "None", "0.140", "0.434", "0.918", "5.256", "−137.1"],
   ["", "Max, clip", "0.146", "0.432", "0.914", "0.012", "−134.5"],
   ["", "Max, scale", "0.129", "0.432", "0.909", "0.011", "−132.5"],
   ["", "Sum, scale", "0.112", "0.474", "0.868", "0.012", "−126.1"],
   ["", "Sum, scale, wide", "0.091", "0.710", "0.738", "0.011", "−119.4"],
   ["Largest (8, 50)", "None", "0.137", "0.371", "1.026", "17.630", "−169.9"],
   ["", "Max, clip", "0.146", "0.368", "1.006", "0.037", "−161.8"],
   ["", "Max, scale", "0.112", "0.397", "0.963", "0.034", "−152.9"],
   ["", "Sum, scale", "0.100", "0.478", "0.874", "0.025", "−133.8"],
   ["", "Sum, scale, wide", "0.083", "0.738", "0.725", "0.010", "−119.9"]],
  [1500, 1500, 1150, 1050, 1050, 1300, 1476]));
C.push(P({ t: "*Time per 30 s episode at which the applied pair violates the time-separated requirement (8). Wide: Δf_lim = 0.5 Hz, RoCoF_lim = 2 Hz/s as in [16].", size: 17, i: true }));
C.push(...FIGURE("fig_headroom_ablation.png", 0, 0, 6.4, "Fig. 3. Feasibility rules applied to five fixed settings: converter saturation, worst-event nadir and objective return (means over 200 test scenarios)."));
C.push(H2("C. Learned schedules on the test set"));
C.push(P("Table V compares all controllers. Without fast support the diesel-only system collapses in 97.5 % of the scenarios, and BESS droop without inertia keeps the system stable but at a RoCoF of 5.5 Hz/s. Every VSG variant keeps the frequency within limits. The tuned fixed setting reaches the best return. For all ten learned runs, the best validation checkpoint was the untrained agent, which is the tuned setting itself, so validation-based selection returns the base controller. The final TD3 policies take a different position on the same trade-off: compared with the tuned setting they reduce the nadir by 0.061 Hz (better in 85 % of the scenarios, p_Holm ≈ 7×10", SUP("−21"), ") but use 0.067 kWh more BESS energy per episode (p_Holm ≈ 10", SUP("−31"), "), with no significant change in RoCoF and a return that is 13.5 points lower. DDPG is worse than TD3 on nadir, RoCoF and return (all p_Holm < 10", SUP("−9"), ")."));
C.push(...TABLE("TABLE V. Test-set results (200 scenarios; learned controllers averaged over 5 seeds)",
  ["Controller", "Nadir (Hz)", "RoCoF (Hz/s)", "BESS (kWh)", "Saturation (s)", "Infeasible (s)", "Return"],
  [["Fixed VSG, tuned (3 s, 15 pu)", "0.573", "1.474", "0.775", "0.103", "2.330", "−105.9"],
   ["Fixed VSG, tuned + projection", "0.573", "1.479", "0.775", "0.123", "0.007", "−106.1"],
   ["TD3 / DDPG, validation-selected", "0.573", "1.479", "0.775", "0.123", "0.007", "−106.1"],
   ["Fixed VSG, standard (3 s, 20 pu)", "0.508", "1.452", "0.934", "0.126", "2.340", "−115.8"],
   ["Bang-bang VSG [5]", "0.505", "1.423", "0.936", "0.121", "2.989", "−116.4"],
   ["TD3, final policy", "0.522", "1.482", "0.849", "0.136", "0.019", "−122.0"],
   ["TD3 without projection, final", "0.540", "1.457", "0.832", "0.108", "5.069", "−124.2"],
   ["DDPG, final policy", "0.596", "1.594", "0.845", "0.128", "0.022", "−133.4"],
   ["BESS droop (no inertia)", "0.732", "5.520", "0.927", "0.645", "1.103", "−286.8"],
   ["Diesel only", "3.06†", "7.38", "0", "0", "0", "−557.7"]],
  [2826, 950, 1050, 1000, 1100, 1100, 1000]));
C.push(P({ t: "†97.5 % of the episodes collapse. Saturation and infeasible-commitment times are per 30 s episode.", size: 17, i: true }));
C.push(...FIGURE("fig_response_sc32.png", 0, 0, 4.6, "Fig. 4. Test scenario 32 (load increase, then load rejection): frequency deviation, RoCoF, VSG power and scheduled virtual inertia."));
C.push(H2("D. What the projection prevents in a learner"));
C.push(P("Trained without the projection, TD3 learns to commit more than the converter can deliver: on every seed the final policy holds an infeasible pair for 3.9–7.2 s of each episode (mean 5.07 s), more than twice the 2.33 s of the tuned fixed setting. With the projection, this falls to 0.02 s and is lower in 98 % of the scenarios (Table VI); the nadir also improves slightly. For the tuned fixed setting the projection removes infeasible commitments at a return cost of 0.13. The projection used here clips each parameter; Section VII.2 indicates that proportional derating would reduce saturation further for aggressive commands."));
C.push(...TABLE("TABLE VI. Effect of the projection (paired Wilcoxon tests, 200 test scenarios)",
  ["Controller", "Metric", "With", "Without", "p-value"],
  [["TD3 final policy", "Infeasible commitments (s)", "0.019", "5.069", "6×10⁻³² (Holm)"],
   ["TD3 final policy", "Nadir (Hz)", "0.522", "0.540", "3×10⁻⁶ (Holm)"],
   ["TD3 final policy", "Objective return", "−122.0", "−124.2", "0.087 (Holm, n.s.)"],
   ["Tuned fixed VSG", "Infeasible commitments (s)", "0.007", "2.330", "4×10⁻⁷"],
   ["Tuned fixed VSG", "Objective return", "−106.1", "−105.9", "0.004"]],
  [1826, 2400, 1300, 1300, 2200]));
C.push(H2("E. Dominance without reward weights"));
C.push(P("Fig. 5 places each controller against the 24 fixed settings in three trade-offs between VSG fast energy and band violation, nadir and RoCoF. No fixed setting is at least as good as the final TD3 policy in all four objectives at once, so TD3 is not dominated, but its nadir is close to that of a fixed setting with D_v ≈ 17 pu; DDPG is dominated by the tuned setting. Fig. 6 shows why learning stalls: the agents start at the base controller and move below it, because the attainable improvement (about 2 %) is smaller than the spread of returns across operating points and events, which the critic cannot resolve."));
C.push(...FIGURE("fig_pareto.png", 0, 0, 6.4, "Fig. 5. Controllers against the fixed settings (grey) and their attainable front (dashed). Error bars: ±1 s.d. over seeds."));
C.push(...FIGURE("fig_learning_curves.png", 0, 0, 4.2, "Fig. 6. Validation return during training (mean ± s.d. over 5 seeds); dashed: untrained agent = tuned setting."));
C.push(H2("F. Validation"));
C.push(P({ t: "Cross-implementation. ", b: true }, "The complete model, including the EMS, the projection and the exported TD3 actor, was re-implemented independently in MATLAB (R2021a, no toolboxes). On twelve test scenarios with identical noise sequences, the traces of both fixed controllers are identical to the Python results and the TD3 traces differ by at most 1.1×10", SUP("−7"), " Hz, due to single-precision arithmetic in the network; all metrics agree to within 0.01 % (Table VII)."));
C.push(P({ t: "Circuit-level model. ", b: true }, "A three-phase 400 V model was built with the same parameters: an average-model VSG converter (three controlled voltage sources) behind its coupling impedance, the diesel SG as an internal voltage behind its reactance with the swing equation, governor and AGC, the load, wind and PV base power as a grid-following injection synchronised to its own PLL, and a 2 % resistive shunt load. The coupling reactances equal the inverse synchronising coefficients of the averaged model (X_v = 0.5 pu, X_d = 1.25 pu, X/R = 10), so that differences arise only from what the averaged model neglects: network electromagnetics, the nonlinear power–angle relation, voltage and reactive power, the PLL (20 Hz bandwidth, then the same 20 ms filter) and a converter power limiter acting on measured power. The VSG swing equation acts on measured converter power, the control code is identical to that of the averaged model, and the circuit is solved at 100 µs after a 0.5 s warm-up. ", EMT.solver_note));
C.push(P("Over the twelve scenarios and three controllers, the frequency deviation of the EMT model follows the averaged model with an RMS difference of ", EMT.rmse_range, " Hz (Fig. 7, Table VII). The worst-event nadir agrees within 2 % (0.531 against 0.540 Hz for the tuned setting and 0.512 against 0.502 Hz for TD3), and the BESS energy within 1.1 %. The largest RoCoF over 100 ms is about ", EMT.rocof100_factor, " times higher in the EMT model: at each load step the bus-voltage phase jumps by roughly 3° because the step current flows through the coupling reactances, and the PLL reads this phase jump as a brief frequency spike, which the averaged model cannot represent. Over a 500 ms window, the window commonly used for RoCoF protection, the difference reduces to between −0.5 % and +9 %; the RoCoF of the diesel rotor itself, a physical quantity without phase-jump content, is 2.2 Hz/s over 100 ms. The projected controllers keep infeasible commitments at ", EMT.infeasible_emt, " per episode in the EMT model. Converter saturation is the one metric that the averaged model clearly underestimates: in the EMT model the power limiter acts on measured power, which includes the electromagnetic transient in the first cycles after each step, and it is active 2.2–2.8 times longer (0.30–0.38 s against 0.11–0.17 s per episode). The ordering of the three controllers is the same in both models for every metric."));
C.push(...TABLE("TABLE VII. Validation summary (12 test scenarios × 3 controllers)",
  ["Check", "Quantity", "Result"],
  [["MATLAB vs Python", "max |ΔΔf|, fixed / projected / TD3", "0 / 0 / 1.1×10⁻⁷ Hz"],
   ["MATLAB vs Python", "Mean metrics (nadir, RoCoF, BESS energy, return)", "identical to 0.01 %"],
   ["EMT vs averaged model", "RMS difference of Δf", EMT.rmse_range + " Hz"],
   ["EMT vs averaged model", "Worst-event nadir", "within 2 % (fixed and TD3)"],
   ["EMT vs averaged model", "BESS energy", "within 1.1 %"],
   ["EMT vs averaged model", "RoCoF over 100 ms / 500 ms", "×" + EMT.rocof100_factor + " / −0.5 to +9 %"],
   ["EMT vs averaged model", "Converter saturation time", "×2.2–2.8 (same ordering)"],
   ["EMT, projected controllers", "Infeasible commitments", EMT.infeasible_emt]],
  [2400, 3700, 2926]));
C.push(...FIGURE("fig_simscape_sc1.png", 0, 0, 6.2, "Fig. 7. Averaged (RMS) model and three-phase Simscape Electrical model for test scenario 1: frequency deviation and VSG power for the three controllers (MATLAB R2021a)."));

// ===== VIII. DISCUSSION =====
C.push(H1("VIII. Discussion"));
C.push(P({ t: "Consistency with the converter-only studies. ", b: true }, "Three findings of [16] carry over to a system with physical inertia: a well-tuned constant setting is hard to beat, damping buys more regulation per unit of headroom than inertia, and literature-style high gains are often undeliverable. What changes is the reason the margin is small. In a converter-only system the learned controllers could still reduce the reserved headroom by about one fifth [16]; here the synchronous coupling fixes the initial share of each step and secondary control shortens the transient, so the oracle leaves only about 2 % to gain."));
C.push(P({ t: "When to train an agent. ", b: true }, "The oracle bound costs a few hundred simulations and no training. It answers whether a given plant offers enough room for adaptation to justify RL. Larger margins are expected with weaker grid-forming coupling, slow or absent secondary control, events that are large relative to the headroom, or uncertain plant parameters; this study suggests running the bound first in such cases."));
C.push(P({ t: "Designing the feasibility layer. ", b: true }, "The time-separated requirement keeps the authority of moderate settings, while the summed requirement, particularly with wide limits, removes most of it. Proportional derating, as introduced in [16], is preferable to clipping because it lowers saturation for every setting tested. A combination of the time-separated requirement (8) with proportional derating (9) is therefore recommended for deployment; retraining the agents with it is left for future work."));
C.push(P({ t: "Averaged versus circuit-level models. ", b: true }, "The averaged model reproduces the frequency trajectories and the energy metrics closely enough to train and rank controllers, but it underestimates the RoCoF that a PLL-based measurement reports immediately after a step and the time a converter spends at its power limit. Studies that set RoCoF limits from averaged models should evaluate RoCoF over windows long enough to exclude phase-jump spikes, or include the phase jump explicitly."));
C.push(P({ t: "Limitations. ", b: true }, "The network is a single bus, the load profile is synthetic, and one site and one year are used. The EMT model represents the converter by its average model and the diesel unit by a classical machine model; switching effects, inner current loops, the excitation system and protection are not modelled; hardware-in-the-loop tests remain to be carried out."));

// ===== IX. CONCLUSION =====
C.push(H1("IX. Conclusion"));
C.push(P("For a hybrid diesel–PV–wind–BESS microgrid driven by a year of site data, the benefit of adapting the inertia and damping of a grid-forming battery converter was bounded before any training: a per-scenario oracle improved on the best fixed setting by only 2.1 %, because the synchronous coupling and secondary control leave the VSG parameters little to shape. Residual TD3 and DDPG agents did not exceed a validation-tuned setting on the objective; TD3 found a non-dominated point with a lower nadir and higher battery use. A direction-aware, time-separated headroom requirement kept learned schedules feasible, reducing undeliverable commitments from 5.07 s to 0.02 s per episode, and proportional derating proved preferable to clipping, whereas the summed requirement of earlier work was overly conservative for moderate settings. A MATLAB re-implementation and a three-phase EMT model confirmed the averaged-model frequency trajectories and the controller ranking, while showing that phase jumps inflate PLL-measured RoCoF and that limiter activity is underestimated by the averaged model. Future work will apply the oracle to plants with weaker grid-forming coupling, retrain the agents with proportional derating, use measured load and multi-bus networks, and test the controllers in hardware-in-the-loop experiments."));

C.push(H1("Data and Code Availability"));
C.push(P("The code, the 2024 input data, the configuration files and the scripts that reproduce every table and figure (Python, MATLAB and the EMT model) are available at ", TODO("public GitHub URL or Zenodo DOI"), ". ERA5 data: Copernicus Climate Change Service; solar data: NASA POWER Project."));
C.push(H1("Acknowledgements"));
C.push(P("This work was supported by the Vidhetbundit Scholarship, Suranaree University of Technology, Thailand. ", TODO("confirm funding statement")));

// ===== REFERENCES =====
C.push(H1("References"));
const REFS = [
  "F. Milano, F. Dörfler, G. Hug, D. J. Hill and G. Verbič, “Foundations and challenges of low-inertia systems,” in Proc. Power Systems Computation Conference (PSCC), 2018.",
  "A. Ulbig, T. S. Borsche and G. Andersson, “Impact of low rotational inertia on power system stability and operation,” IFAC Proceedings Volumes, vol. 47, no. 3, pp. 7290–7297, 2014.",
  "Q.-C. Zhong and G. Weiss, “Synchronverters: Inverters that mimic synchronous generators,” IEEE Trans. Ind. Electron., vol. 58, no. 4, pp. 1259–1267, 2011.",
  "H. Bevrani, T. Ise and Y. Miura, “Virtual synchronous generators: A survey and new perspectives,” Int. J. Electr. Power Energy Syst., vol. 54, pp. 244–254, 2014.",
  "J. Alipoor, Y. Miura and T. Ise, “Power system stabilization using virtual synchronous generator with alternating moment of inertia,” IEEE J. Emerg. Sel. Topics Power Electron., vol. 3, no. 2, pp. 451–458, 2015.",
  "D. Li et al., “A self-adaptive inertia and damping combination control of VSG to support frequency stability,” IEEE Trans. Energy Convers., vol. 32, no. 1, pp. 397–398, 2017.",
  "T. Shi et al., “Research on adaptive optimal control strategy of virtual synchronous generator inertia and damping parameters,” IET Power Electron., vol. 17, no. 1, pp. 121–133, 2024.",
  "J. Han et al., “Adaptive VSG control strategy considering energy storage SOC constraints,” Front. Energy Res., vol. 11, 1278648, 2023.",
  "M. A. Afifi, M. I. Marei and A. M. Mohamad, “Reinforcement learning approach with deep deterministic policy gradient DDPG-controlled virtual synchronous generator for an islanded microgrid,” in Proc. 24th Int. Middle East Power System Conf. (MEPCON), 2023.",
  "C. Lu and X. Zhuan, “Adaptive control for virtual synchronous generator parameters based on soft actor critic,” Sensors, vol. 24, no. 7, 2035, 2024.",
  "O. E. Egbomwan, S. Liu and H. Chaoui, “Twin delayed deep deterministic policy gradient (TD3) based virtual inertia control for inverter-interfacing DGs in microgrids,” IEEE Syst. J., vol. 17, no. 2, pp. 2122–2132, 2023.",
  "O. Oboreh-Snapps et al., “Virtual synchronous generator control using twin delayed deep deterministic policy gradient method,” IEEE Trans. Energy Convers., vol. 39, no. 1, pp. 214–228, 2024.",
  "J. Li et al., “Adaptive VSG control method based on reinforcement learning strategy optimization,” Electr. Power Syst. Res., vol. 257, 112997, 2026.",
  "A. Criollo et al., “Enhancing virtual inertia control in microgrid clusters: A novel frequency response model based on deep reinforcement learning,” Appl. Sci., vol. 16, no. 13, 6685, 2026.",
  "M. B. Khan, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Reinforcement learning based virtual synchronous generator control for a low inertia solar–wind–BESS microgrid: A converter headroom-feasible approach,” under review. [AUTHOR: update status]",
  "M. B. Khan, P. Pao-La-Or, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Headroom-feasible adaptive virtual synchronous generator control with deep reinforcement learning: A multi-seed comparison with tuned controllers,” submitted. [AUTHOR: update status]",
  "S. Fujimoto, H. van Hoof and D. Meger, “Addressing function approximation error in actor-critic methods,” in Proc. 35th Int. Conf. Machine Learning (ICML), 2018.",
  "T. P. Lillicrap et al., “Continuous control with deep reinforcement learning,” in Proc. Int. Conf. Learning Representations (ICLR), 2016.",
  "T. Silver, K. Allen, J. Tenenbaum and L. Kaelbling, “Residual policy learning,” arXiv:1812.06298, 2018.",
  "H. Hersbach et al., “The ERA5 global reanalysis,” Q. J. R. Meteorol. Soc., vol. 146, no. 730, pp. 1999–2049, 2020.",
  "NASA Prediction Of Worldwide Energy Resources (POWER) Project, hourly data, https://power.larc.nasa.gov",
  "IEC 61400-12-1:2017, Wind energy generation systems — Part 12-1: Power performance measurements of electricity producing wind turbines.",
  "Commission Regulation (EU) 2017/1485 of 2 August 2017 establishing a guideline on electricity transmission system operation, Annex III.",
  "P. Kundur, Power System Stability and Control. New York: McGraw-Hill, 1994.",
  "F. Wilcoxon, “Individual comparisons by ranking methods,” Biometrics Bulletin, vol. 1, no. 6, pp. 80–83, 1945.",
  "S. Holm, “A simple sequentially rejective multiple test procedure,” Scand. J. Statist., vol. 6, no. 2, pp. 65–70, 1979.",
  "P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup and D. Meger, “Deep reinforcement learning that matters,” in Proc. AAAI Conf. Artificial Intelligence, 2018.",
  "R. Agarwal et al., “Deep reinforcement learning at the edge of the statistical precipice,” in Advances in Neural Information Processing Systems, vol. 34, pp. 29304–29320, 2021.",
  "A. D. Paquette and D. M. Divan, “Virtual impedance current limiting for inverters in microgrids with synchronous generators,” IEEE Trans. Ind. Appl., vol. 51, no. 2, pp. 1630–1638, 2015.",
  "T. Qoria et al., “Current limiting algorithms and transient stability analysis of grid-forming VSCs,” Electr. Power Syst. Res., vol. 189, 106726, 2020.",
  "M. Glavic, “(Deep) reinforcement learning for electric power system control and related problems: A short review and perspectives,” Annu. Rev. Control, vol. 48, pp. 22–35, 2019.",
];
REFS.forEach((r, i) => {
  const m = r.match(/^(.*?)( \[AUTHOR: [^\]]*\])?$/);
  const parts = [`[${i + 1}] `, m[1]];
  if (m[2]) parts.push({ t: m[2], hl: true });
  C.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 }, indent: { left: 340, hanging: 340 }, children: runs(parts, 16) }));
});
C.push(new Paragraph({ spacing: { before: 120 }, children: runs([TODO("check the year, volume and pages of every reference against the publisher page (DOI list: docs/PROPOSAL_REFERENCES.md)")], 16) }));

// ---------- Authors' information (as in the authors' IREMOS manuscript) ----------
const AI = (...parts) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100 }, children: runs(parts, 16) });
C.push(H1("Authors’ information"));
C.push(AI({ t: "1", sup: true }, "School of Electrical Engineering, Institute of Engineering, Suranaree University of Technology, 111 University Avenue, Suranaree Sub-district, Mueang Nakhon Ratchasima District, Nakhon Ratchasima 30000, Thailand."));
C.push(AI({ t: "2", sup: true }, "Department of Electrical and Computer Engineering, Faculty of Engineering, Naresuan University, 99 Moo 9, Tha Pho Sub-district, Mueang Phitsanulok District, Phitsanulok 65000, Thailand."));
C.push(AI("Corresponding author: Muhammad Binyameen Khan, Tel.: +66 65 226 6437, E-mail: binyameen2210@gmail.com, postal address as in affiliation 1. ", TODO("confirm corresponding author and contact details")));
C.push(AI(TODO("insert a passport-size photograph before each biography, as in the IREMOS manuscript")));
const BIOS = [
  "Muhammad Binyameen Khan received his bachelor’s degree in Electrical Engineering from ISRA University, Islamabad, Pakistan, and is currently pursuing the M.Sc. degree in Electrical Engineering at Suranaree University of Technology, Thailand. He has more than three years of field experience in solar PV installation and grid-connected inverter systems. His research interests include deep reinforcement learning for power systems, grid-forming converter control and virtual inertia in low-inertia microgrids.",
  "Padej Pao-La-Or received the B.Eng., M.Eng. and D.Eng. degrees in Electrical Engineering from Suranaree University of Technology, Thailand, where he is currently an Associate Professor. His research interests include electromagnetic-field analysis, finite-element methods, thermal analysis, optimization and electric-machine analysis.",
  "Arthit Srikaew received the B.Eng. degree in Electronics Engineering from King Mongkut’s Institute of Technology Ladkrabang, Thailand, and the M.S. and Ph.D. degrees in Electrical Engineering from Vanderbilt University, USA. He is currently an Associate Professor at Suranaree University of Technology. His research interests include robotics, artificial intelligence, intelligent control, machine learning and automation.",
  "Tosaphol Ratniyomchai received the B.Eng. degree with First Class Honors and the M.Eng. degree in Electrical Engineering from Suranaree University of Technology, Thailand, and the Ph.D. degree in Electronic and Electrical Engineering from the University of Birmingham, United Kingdom. He is currently an Assistant Professor at Suranaree University of Technology. His research interests include power-system simulation, power quality, railway electrification, energy storage and sustainable electric transport.",
  "Jirawadee Polprasert received the B.Eng. degree in Electrical Engineering from Suranaree University of Technology, Thailand, and the M.Eng. and D.Eng. degrees in Energy (Electric Power System Management) from the Asian Institute of Technology, Thailand. She is currently an Assistant Professor at Naresuan University. Her research interests include power-system planning, operation and control, artificial intelligence in power systems, optimization, distributed generation and renewable energy.",
  "Anant Oonsivilai received the B.Eng. degree in Electrical Engineering from Khon Kaen University, Thailand, the M.Eng. degree in Electrical Engineering from King Mongkut’s University of Technology North Bangkok, Thailand, and the Ph.D. degree in Electrical and Computer Engineering from Dalhousie University, Canada. He is currently an Associate Professor at Suranaree University of Technology and a Senior Fellow of the Higher Education Academy (SFHEA). His research interests include electrical power systems, renewable energy, artificial intelligence, dynamic and stability analysis, and optimization.",
];
BIOS.forEach((b) => { const [n1, n2, ...rest] = b.split(" "); C.push(AI({ t: `${n1} ${n2} `, b: true }, rest.join(" "))); });

// ---------- document: one-column title block, then two columns with full-width figures and tables ----------
const PAGE = { size: { width: 11906, height: 16838 }, margin: { top: 1383, right: 850, bottom: 1701, left: 1417, header: 312, footer: 1134 } };
const sections = [{ properties: { page: PAGE }, children: HEAD }];
let buf = [];
const flush = () => { if (buf.length) { sections.push({ properties: { page: PAGE, type: SectionType.CONTINUOUS, column: { count: 2, space: 567 } }, children: buf }); buf = []; } };
for (const el of C) {
  if (el && el.wide) { flush(); sections.push({ properties: { page: PAGE, type: SectionType.CONTINUOUS }, children: el.wide }); }
  else buf.push(el);
}
flush();
const doc = new Document({
  creator: "Muhammad Binyameen Khan", title: "IREA manuscript (PWP template)",
  styles: { default: { document: { run: { font: FONT, size: BODY } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 340, hanging: 227 } } } }] }] },
  sections,
});
Packer.toBuffer(doc).then((b) => { const out = path.join(__dirname, "IREA_manuscript_PWP.docx"); fs.writeFileSync(out, b); console.log("wrote", out); });
