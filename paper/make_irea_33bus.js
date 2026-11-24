// IEEE 33-bus manuscript (Study 3) in the Praise Worthy Prize template used for the IREA manuscript.
// Every number comes from study3_ieee33/results (paper_numbers.json and the CSV files); nothing is typed by hand
// except the plant parameters, which are those of study3_ieee33/configs/ieee33.yaml.
// Run: python study3_ieee33/scripts/paper_figures.py && python paper/ieee33_equations.py && node paper/make_irea_33bus.js
//      -> paper/IREA_33bus_manuscript_PWP.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  ShadingType, BorderStyle, LevelFormat, SectionType,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const S3 = path.join(ROOT, "study3_ieee33");
const FIGP = (f) => path.join(S3, "results", "figures", f);
const N = JSON.parse(fs.readFileSync(path.join(S3, "results", "paper_numbers.json"), "utf8"));
const FONT = "Times New Roman";
const BODY = 20;
const FULL_W = 9639;
const COL_W = 4536;

// ---------- numbers ----------
const f2 = (x) => x.toFixed(2), f3 = (x) => x.toFixed(3), f1 = (x) => x.toFixed(1);
const T = N.test;
const pct = (a, b) => (100 * (a - b) / Math.abs(b));
const pe = (p) => { if (p >= 0.001) return p.toFixed(3); const e = Math.floor(Math.log10(p)); const sup = String(e).replace(/-/g, "⁻").replace(/\d/g, (d) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[d]); return `${(p / 10 ** e).toFixed(1)} × 10${sup}`; };
const H = (vs, m) => N.holm[`${vs}|${m}`];            // [median diff, TD3-better fraction, p, p_holm]
const PD = (k, m) => N.paired[k][m];
const conv = Object.fromEntries(N.convergence.summary.map((r) => [r.run, r]));
const convSeeds = N.convergence.seeds;
const omNom = N.oracle_map.find((r) => r.bess_frac === 0.625 && r.diesel_mva === 4.9 && r.event_factor === 1.0);
const omMax = N.oracle_map.reduce((a, b) => (a.oracle_gain_pct > b.oracle_gain_pct ? a : b));
const evNom = N.oracle_event.find((r) => r.condition === "nominal");
const evRoom = N.oracle_event.find((r) => r.condition === "most_room");
const hp = Object.fromEntries(N.hp_screen.map((r) => [`${r.algo}_${r.h}`, r]));
const sd = (xs) => { const m = xs.reduce((a, b) => a + b, 0) / xs.length; return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1)); };
const gainUntuned = pct(T.fixed_tuned.return[0], T.fixed.return[0]);
const gainTd3Untuned = pct(T.td3.return[0], T.fixed.return[0]);
const OCI = N.oracle_ci, VOLT = N.voltage, HALF = N.half, HP2 = N.half_paired;
const WT = Object.fromEntries(N.weights.map((r) => [r.weighting, r]));
const GRID = OCI.fixed_grid_val;
const nadirRed = -pct(T.td3.nadir_hz[0], T.fixed_tuned.nadir_hz[0]);
const ci = (a) => `${f2(Math.max(a[1], 0))}–${f2(a[2])}`;

// ---------- references, numbered in order of first citation ----------
const REF = {
  milano: "F. Milano, F. Dörfler, G. Hug, D. J. Hill and G. Verbič, “Foundations and challenges of low-inertia systems,” in Proc. Power Systems Computation Conference (PSCC), 2018.",
  ulbig: "A. Ulbig, T. S. Borsche and G. Andersson, “Impact of low rotational inertia on power system stability and operation,” IFAC Proceedings Volumes, vol. 47, no. 3, pp. 7290–7297, 2014.",
  zhong: "Q.-C. Zhong and G. Weiss, “Synchronverters: Inverters that mimic synchronous generators,” IEEE Trans. Ind. Electron., vol. 58, no. 4, pp. 1259–1267, 2011.",
  bevrani: "H. Bevrani, T. Ise and Y. Miura, “Virtual synchronous generators: A survey and new perspectives,” Int. J. Electr. Power Energy Syst., vol. 54, pp. 244–254, 2014.",
  alipoor: "J. Alipoor, Y. Miura and T. Ise, “Power system stabilization using virtual synchronous generator with alternating moment of inertia,” IEEE J. Emerg. Sel. Topics Power Electron., vol. 3, no. 2, pp. 451–458, 2015.",
  li17: "D. Li, Q. Zhu, S. Lin and X. Y. Bian, “A self-adaptive inertia and damping combination control of VSG to support frequency stability,” IEEE Trans. Energy Convers., vol. 32, no. 1, pp. 397–398, 2017.",
  shi: "T. Shi et al., “Research on adaptive optimal control strategy of virtual synchronous generator inertia and damping parameters,” IET Power Electron., vol. 17, no. 1, pp. 121–133, 2024.",
  han: "J. Han et al., “Adaptive VSG control strategy considering energy storage SOC constraints,” Front. Energy Res., vol. 11, 1278648, 2023.",
  afifi: "M. A. Afifi, M. I. Marei and A. M. Mohamad, “Reinforcement learning approach with deep deterministic policy gradient DDPG-controlled virtual synchronous generator for an islanded microgrid,” in Proc. 24th Int. Middle East Power System Conf. (MEPCON), 2023.",
  lu: "C. Lu and X. Zhuan, “Adaptive control for virtual synchronous generator parameters based on soft actor critic,” Sensors, vol. 24, no. 7, 2035, 2024.",
  egbomwan: "O. E. Egbomwan, S. Liu and H. Chaoui, “Twin delayed deep deterministic policy gradient (TD3) based virtual inertia control for inverter-interfacing DGs in microgrids,” IEEE Syst. J., vol. 17, no. 2, pp. 2122–2132, 2023.",
  oboreh: "O. Oboreh-Snapps et al., “Virtual synchronous generator control using twin delayed deep deterministic policy gradient method,” IEEE Trans. Energy Convers., vol. 39, no. 1, pp. 214–228, 2024.",
  lij: "J. Li et al., “Adaptive VSG control method based on reinforcement learning strategy optimization,” Electr. Power Syst. Res., vol. 257, 112997, 2026.",
  criollo: "A. Criollo et al., “Enhancing virtual inertia control in microgrid clusters: A novel frequency response model based on deep reinforcement learning,” Appl. Sci., vol. 16, no. 13, 6685, 2026.",
  glavic: "M. Glavic, “(Deep) reinforcement learning for electric power system control and related problems: A short review and perspectives,” Annu. Rev. Control, vol. 48, pp. 22–35, 2019.",
  henderson: "P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup and D. Meger, “Deep reinforcement learning that matters,” in Proc. AAAI Conf. Artificial Intelligence, 2018.",
  agarwal: "R. Agarwal, M. Schwarzer, P. S. Castro, A. Courville and M. G. Bellemare, “Deep reinforcement learning at the edge of the statistical precipice,” in Advances in Neural Information Processing Systems, vol. 34, pp. 29304–29320, 2021.",
  khanTrec: "M. B. Khan, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Reinforcement learning based virtual synchronous generator control for a low inertia solar–wind–BESS microgrid: A converter headroom-feasible approach,” under review. [AUTHOR: update status]",
  khanIremos: "M. B. Khan, P. Pao-La-Or, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Headroom-feasible adaptive virtual synchronous generator control with deep reinforcement learning: A multi-seed comparison with tuned controllers,” submitted. [AUTHOR: update status]",
  khanIrea: "M. B. Khan, P. Pao-La-Or, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Bounding the benefit of learned virtual-inertia scheduling in a hybrid diesel–PV–wind–BESS microgrid: Oracle analysis, headroom projection and circuit-level validation,” submitted to Int. J. Eng. Appl. (IREA). [AUTHOR: update status]",
  baran: "M. E. Baran and F. F. Wu, “Network reconfiguration in distribution systems for loss reduction and load balancing,” IEEE Trans. Power Del., vol. 4, no. 2, pp. 1401–1407, 1989.",
  matpower: "R. D. Zimmerman, C. E. Murillo-Sánchez and R. J. Thomas, “MATPOWER: Steady-state operations, planning, and analysis tools for power systems research and education,” IEEE Trans. Power Syst., vol. 26, no. 1, pp. 12–19, 2011.",
  pandapower: "L. Thurner et al., “pandapower—An open-source Python tool for convenient modeling, analysis, and optimization of electric power systems,” IEEE Trans. Power Syst., vol. 33, no. 6, pp. 6510–6521, 2018.",
  mahtani: "K. Mahtani, J. Muñoz-Antón, S. B. Lee and C. A. Platero, “Online diagnostics of brushless synchronous machine exciter field winding through temperature and resistance measurement,” IEEE Trans. Ind. Appl., vol. 61, no. 3, pp. 3774–, 2025. [AUTHOR: add the last page]",
  ieee4215: "IEEE Recommended Practice for Excitation System Models for Power System Stability Studies, IEEE Std 421.5-2016, 2016.",
  ieee1547: "IEEE Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces, IEEE Std 1547-2018, 2018.",
  narang: "D. Narang, “Highlights of IEEE Standard 1547-2018,” National Renewable Energy Laboratory webinar, Oct. 2019 (rev. Nov. 2019).",
  opender: "Electric Power Research Institute (EPRI), “OpenDER: Open-source distributed energy resource model,” version 2.2.0. [AUTHOR: complete with the OpenDER reference you hold (report number or URL)]",
  unifi: "UNIFI Consortium, “UNIFI specifications for grid-forming inverter-based resources, version 3,” UNIFI-2026-2-1 (NLR/TP-5D00-98381), Jan. 2026.",
  liu: "R. Liu, L. Ding, C. Xue and Y. W. Li, “Small-signal modelling and analysis of microgrids with synchronous and virtual synchronous generators,” IET Energy Syst. Integr., vol. 6, no. 1, 2024, doi: 10.1049/esi2.12099.",
  kundur: "P. Kundur, Power System Stability and Control. New York: McGraw-Hill, 1994.",
  era5: "H. Hersbach et al., “The ERA5 global reanalysis,” Q. J. R. Meteorol. Soc., vol. 146, no. 730, pp. 1999–2049, 2020.",
  power: "NASA Prediction Of Worldwide Energy Resources (POWER) Project, hourly data, https://power.larc.nasa.gov",
  iec61400: "IEC 61400-12-1:2017, Wind energy generation systems — Part 12-1: Power performance measurements of electricity producing wind turbines.",
  egat: "P. Bunnak, “Thai power system: Hourly power generation, demand, and cross-border flows,” Zenodo, version 1.0, Sep. 13, 2025, doi: 10.5281/zenodo.17109911.",
  soguide: "Commission Regulation (EU) 2017/1485 of 2 August 2017 establishing a guideline on electricity transmission system operation, Annex III.",
  rocof: "ENTSO-E, “Rate of change of frequency (RoCoF) withstand capability,” ENTSO-E guidance document for national implementation for network codes on grid connection, Brussels, Belgium, Jan. 31, 2018.",
  sugeno: "T. Takagi and M. Sugeno, “Fuzzy identification of systems and its applications to modeling and control,” IEEE Trans. Syst., Man, Cybern., vol. SMC-15, no. 1, pp. 116–132, 1985.",
  silver: "T. Silver, K. Allen, J. Tenenbaum and L. Kaelbling, “Residual policy learning,” arXiv:1812.06298, 2018.",
  fujimoto: "S. Fujimoto, H. van Hoof and D. Meger, “Addressing function approximation error in actor-critic methods,” in Proc. 35th Int. Conf. Machine Learning (ICML), 2018.",
  lillicrap: "T. P. Lillicrap et al., “Continuous control with deep reinforcement learning,” in Proc. Int. Conf. Learning Representations (ICLR), 2016.",
  wilcoxon: "F. Wilcoxon, “Individual comparisons by ranking methods,” Biometrics Bulletin, vol. 1, no. 6, pp. 80–83, 1945.",
  holm: "S. Holm, “A simple sequentially rejective multiple test procedure,” Scand. J. Statist., vol. 6, no. 2, pp. 65–70, 1979.",
  egbomwan25: "O. E. Egbomwan, S. Liu, H. Chaoui and X. Wang, “Learning-based predictive virtual inertia control for frequency regulation in low inertia power grids,” IEEE Open J. Circuits Syst., vol. 6, pp. 504–519, 2025.",
  efron: "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York: Chapman & Hall, 1993.",
};
const order = [];
const cite = (...keys) => "[" + keys.map((k) => {
  if (!REF[k]) throw new Error("unknown reference " + k);
  if (!order.includes(k)) order.push(k);
  return order.indexOf(k) + 1;
}).join("], [") + "]";

// ---------- helpers (as make_irea_pwp.js) ----------
function runs(parts, size = BODY, italic = false) {
  return parts.map((p) => {
    if (typeof p === "string") return new TextRun({ text: p, font: FONT, size, italics: italic });
    return new TextRun({ text: p.t, bold: !!p.b, italics: p.i !== undefined ? !!p.i : italic, font: FONT, size: p.size || size,
      superScript: !!p.sup, subScript: !!p.sub,
      shading: p.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined });
  });
}
const TODO = (t) => ({ t: ` [AUTHOR: ${t}]`, hl: true });
const P = (...parts) => new Paragraph({ children: runs(parts), alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 227 } });
let SEC = "", sub = 0;
const H1 = (t) => {
  const m = t.match(/^([IVX]+)\.\s/); SEC = m ? m[1] : ""; sub = 0;
  return new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 360, after: 120 },
    children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })] });
};
const H2 = (t) => {
  sub += 1;
  return new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 300, after: 120 },
    children: [new TextRun({ text: `${SEC}.${sub}. ${t}`, font: FONT, size: BODY, italics: true })] });
};
let eqN = 0;
const EQ = (key) => { eqN += 1; return new Paragraph({ children: [new TextRun({ text: `@@EQ|${key}|${eqN}@@`, font: FONT, size: BODY })] }); };
const BUL = (...parts) => new Paragraph({ children: runs(parts), numbering: { reference: "bul", level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 } });
const roman = (n) => ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][n - 1];
let figN = 0, tabN = 0;
const FIG_ORDER = ["diagram", "paired", "traces", "conv", "oracle"];
const TAB_ORDER = ["lit", "novel", "nomen", "plant", "learn", "test", "seed", "paired", "conv", "hp", "weights", "half"];
const fref = (k) => { const i = FIG_ORDER.indexOf(k); if (i < 0) throw new Error("figure " + k); return `Fig. ${i + 1}`; };
const tref = (k) => { const i = TAB_ORDER.indexOf(k); if (i < 0) throw new Error("table " + k); return `Table ${roman(i + 1)}`; };
function FIGURE(key, file, widthIn, caption) {
  figN += 1;
  if (FIG_ORDER[figN - 1] !== key) throw new Error(`figure order: ${key}`);
  const buf = fs.readFileSync(FIGP(file));
  const wpx = buf.readUInt32BE(16), hpx = buf.readUInt32BE(20);
  const w = Math.round(Math.min(widthIn, 6.4) * 96), h = Math.round(w * hpx / wpx);
  return [{ wide: [
    new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h },
        altText: { title: `Fig. ${figN}`, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 60, after: 200 }, children: runs([`Fig. ${figN}. ${caption}`], 16) }),
  ] }];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
function TABLE(key, title, header, rows, widths, note) {
  tabN += 1;
  if (TAB_ORDER[tabN - 1] !== key) throw new Error(`table order: ${key}`);
  const tot = widths.reduce((a, b) => a + b, 0);
  const ws = widths.map((w) => Math.floor(w * Math.min(1, FULL_W / tot)));
  const cell = (txt, j, head) => new TableCell({ borders, width: { size: ws[j], type: WidthType.DXA },
    margins: { top: 30, bottom: 30, left: 60, right: 60 },
    shading: !head && txt && txt.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined,
    children: [new Paragraph({ alignment: j === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: [new TextRun({ text: String(txt && txt.t !== undefined ? txt.t : txt), font: FONT, size: 16, bold: head || !!(txt && txt.b) })] })] });
  const out = [
    new Paragraph({ keepNext: true, keepLines: true, alignment: AlignmentType.CENTER, spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: `TABLE ${roman(tabN)}`, font: FONT, size: 16 }), new TextRun({ text: title.toUpperCase(), font: FONT, size: 16, break: 1 })] }),
    new Table({ width: { size: ws.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: ws,
      rows: [header, ...rows].map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true, children: r.map((c, j) => cell(c, j, i === 0)) })) }),
  ];
  if (note) out.push(new Paragraph({ spacing: { before: 40, after: 160 }, children: runs([note], 15) }));
  else out.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return [{ wide: out }];
}

const C = [];
const HL = (t) => ({ t, hl: true });
// =================================================================== I. INTRODUCTION
C.push(H1("I. Introduction"));
C.push(P(`Isolated distribution systems that replace part of their diesel generation with photovoltaic (PV) and wind plants lose rotating inertia: the converter-interfaced sources neither store kinetic energy nor respond to the rate of change of frequency (RoCoF) unless they are told to, so that every load step produces a faster and deeper frequency excursion ${cite("milano", "ulbig")}. A battery energy storage system (BESS) operated as a virtual synchronous generator (VSG) restores part of the missing response by emulating a swing equation with a virtual inertia H`, { t: "v", sub: true }, ` and a damping D`, { t: "v", sub: true }, ` ${cite("zhong", "bevrani")}. Because the best pair (H`, { t: "v", sub: true }, `, D`, { t: "v", sub: true }, `) depends on the operating point and on the disturbance, a long line of work adapts them online, first with rules ${cite("alipoor", "li17", "shi", "han")} and, more recently, with deep reinforcement learning (RL), in particular the deep deterministic policy gradient (DDPG) and its twin-delayed successor TD3 ${cite("afifi", "lu", "egbomwan", "oboreh", "lij", "criollo", "egbomwan25")}.`));
C.push(P(`Most of these studies report that the learned controller outperforms a fixed-parameter VSG and that TD3 outperforms DDPG. The size of the improvement, however, depends on three choices that are rarely examined together: how well the fixed and rule-based baselines are tuned, whether the reported numbers come from scenarios that were also used for training or model selection, and how many random seeds are run ${cite("glavic", "henderson", "agarwal")}. A fourth question is almost never asked: how much could any adaptive scheduler gain on the given plant? Without this bound, a small improvement cannot be told apart from a large share of a small margin, and a large improvement over an untuned baseline cannot be told apart from the gain that simple tuning would have delivered.`));
C.push(P(`The authors' earlier studies examined these questions on single-bus microgrids ${cite("khanTrec", "khanIremos", "khanIrea")} and found that a per-scenario oracle bounds the benefit of adaptation at about 2 % ${cite("khanIrea")}. The present paper asks whether this conclusion survives in a distribution network with voltage dynamics and standard converter functions, and whether it depends on the objective or on the size of the disturbances. The network is the islanded IEEE 33-bus feeder ${cite("baran")} with a published 4.9 MVA diesel machine and its IEEE 421.5 excitation system ${cite("mahtani", "ieee4215")}, a grid-forming BESS-VSG with the reactive-power droop of the UNIFI specification ${cite("unifi")}, and PV and wind plants with the IEEE 1547-2018 frequency-droop and volt-var functions ${cite("ieee1547")}, operated over one year of measured load and weather data.`));
C.push(P("The contributions are:"));
C.push(BUL({ t: "A reproducible benchmark on a published feeder. ", b: true }, "The network, the diesel machine and its exciter, and the converter control functions are taken from published sources and standards, the load and weather inputs are measured data, and every value chosen by the authors is marked as such (", tref("plant"), ")."));
C.push(BUL({ t: "An equal-effort comparison. ", b: true }, "Fixed, bang-bang, RoCoF-adaptive, direction-aware and fuzzy controllers are tuned on the same validation scenarios that select the RL checkpoints; TD3 and DDPG share the code, the budget, five seeds and a hyperparameter screen; all methods are tested on 200 unseen scenarios with paired, multiplicity-corrected tests."));
C.push(BUL({ t: "Oracle bounds with their uncertainty. ", b: true }, "The best possible gain of piecewise-constant scheduling is computed at the scenario level over twelve plant sizings, at the event level, and under five weightings of the objective, with bootstrap intervals."));
C.push(BUL({ t: "Two explanations of the gap to the literature. ", b: true }, `Against an untuned fixed VSG the learned controller improves the objective by ${f1(gainTd3Untuned)} %; against a tuned one it does not. When the disturbances change size after training, TD3 adapts and beats the VSG tuned for the old size, but not one re-tuned for the new size.`));

// =================================================================== II. RELATED WORK
C.push(H1("II. Related Work"));
C.push(P(`Rule-based adaptive VSGs change the inertia and damping with the sign and size of the frequency deviation and its derivative. Alipoor et al. ${cite("alipoor")} switch between two inertia values depending on whether the rotor accelerates away from or towards nominal speed; Li et al. ${cite("li17")} add inertia while the deviation grows and damping in proportion to it; later work optimises the gains ${cite("shi")} or bounds them by the state of charge of the storage ${cite("han")}. Learning-based schedulers replace these rules by a policy trained with DDPG ${cite("afifi")}, soft actor-critic ${cite("lu", "criollo")} or TD3 ${cite("egbomwan", "oboreh", "lij", "egbomwan25")}. ${tref("lit")} lists the test conditions and the results these studies report, each against its own reference.`));
C.push(P({ t: "The reported improvements in frequency deviation, 33–60 %, are measured against fixed-parameter VSGs or PI controllers, with one trained agent per study and one to three disturbances; only one study tunes a baseline by grid search. Because systems, disturbances and baselines differ, the table cannot rank the controllers; it shows how strongly a reported gain depends on its reference. This motivates the protocol of Section V: tuned baselines, held-out test data, several seeds and an oracle bound.", hl: true }));
C.push(...TABLE("lit", "Test conditions and reported results of related studies (each against its own reference)",
  ["Ref.", "Test system", "Validation", "Reference controller", "Reported result"],
  [[`${cite("li17")} rule`, "Single VSG, 50 kW load shedding", "Simulink", "Constant parameters", "Δf 0.75 → 0.45 Hz"],
   [`${cite("shi")} rule`, "Grid-connected VSG, 15 kW step", "Simulink", "Fixed J, D", "Δf 0.5 → 0.2 Hz"],
   [`${cite("han")} rule`, "PV–storage microgrid, 60 kW", "PLECS + HIL", "Constant inertia", "Frequency dip −13 to −55 %"],
   [`${cite("lu")} SAC`, "100 kW VSG, 0 → 20 kW step", "Simulink", "Fixed VSG", "Δf 0.35 → 0.21 Hz"],
   [`${cite("egbomwan")} TD3`, "IEEE 34-node feeder, 3 DGs", "Simulink", "PI", "Mean abs. Δf error −56.6 %"],
   [`${cite("oboreh")} TD3`, "Banshee feeder (PV, BESS), MW", "Simulink + RTDS", "Fixed, fuzzy, DDPG", "Graphical only"],
   [`${cite("egbomwan25")} PINN+TD3`, "IEEE 34/39-bus, 4 × 2 MW DGs", "Simulink", "PI, MPC", "max |Δf| 0.062 → 0.006 Hz"],
   [`${cite("criollo")} SAC`, "Two-area model, PV–wind–diesel", "Simulink (low order)", "PID", "RoCoF −37.23 %"],
   [`${cite("lij")} TD3`, "380 V VSG, 0 → 50 kW step", "Simulink", "Fixed; grid-searched rule", "Δf 1.00 → 0.67 Hz"],
   ["This study", "IEEE 33-bus, 4.9 MVA diesel, measured load, 200 test scenarios", "Phasor model", "Validation-tuned fixed VSG and four tuned rules, 5 seeds", `Objective not improved; |Δf|max −${f1(nadirRed)} %`]].map((r, i) => i < 9 ? r.map((c) => HL(c)) : r),
  [1300, 2500, 1500, 2300, 2039], "Values in yellow are quoted from the cited works and must be checked against them; 50 Hz and 60 Hz systems of different size are included, so rows are not directly comparable."));
C.push(P(`${tref("novel")} states what this paper adds to the authors' earlier single-bus studies.`));
C.push(...TABLE("novel", "What this study adds to the authors' earlier work", ["Aspect", `Earlier studies ${cite("khanTrec", "khanIremos", "khanIrea")}`, "This study"], [
  ["Network", "Single bus; converter-only [" + (order.indexOf("khanTrec") + 1) + "], [" + (order.indexOf("khanIremos") + 1) + "] or diesel + VSG [" + (order.indexOf("khanIrea") + 1) + "]", "IEEE 33-bus feeder, line impedances, voltage dynamics"],
  ["Diesel and converter models", "Classical machine; active-power VSG", "Published salient machine with IEEE 421.5 AC8C exciter; UNIFI Q–V droop; IEEE 1547 droop and volt-var"],
  ["Baselines", "Fixed and tuned VSG; bang-bang and RoCoF-adaptive rules", "Adds direction-aware and fuzzy rules; all rules tuned around the tuned fixed VSG"],
  ["Oracle", "Scenario level, one plant", "Scenario level over 12 sizings, event-wise, five reward weightings, bootstrap intervals"],
  ["Learning protocol", "5 seeds, held-out test weeks", "Adds a convergence test, a hyperparameter screen and a change of disturbance size after training"],
  ["Circuit-level check", "Simscape EMT model [" + (order.indexOf("khanIrea") + 1) + "]", "Not repeated (Section VIII)"],
], [2000, 3500, 4139]));

// =================================================================== III. STUDY SYSTEM
C.push(H1("III. Study System"));
C.push(H2("Feeder, Plant and Data"));
C.push(P(`The network is the IEEE 33-bus radial feeder of Baran and Wu ${cite("baran")} at 12.66 kV, with the published line impedances, the five open tie lines and the published bus loads (3.715 MW and 2.30 Mvar in total). The feeder data were checked against the MATPOWER case ${cite("matpower")}: the base-case losses of 202.68 kW and the minimum voltage of 0.9131 pu at bus 18 are reproduced, and the load flow of the model agrees with pandapower ${cite("pandapower")} within 3 × 10`, { t: "−9", sup: true }, ` pu. The feeder is islanded: the substation at bus 1 is replaced by a diesel synchronous generator, the BESS-VSG is connected at the far end of the main feeder (bus 18) and the PV and wind plants at the far end of the lateral (bus 33), ${fref("diagram")}. The symbols are listed in ${tref("nomen")}.`));
C.push(...FIGURE("diagram", "fig_ieee33_diagram.png", 6.4, "Islanded IEEE 33-bus feeder [" + (order.indexOf("baran") + 1) + "] with the diesel synchronous generator at bus 1, the grid-forming BESS-VSG at bus 18 and the grid-following PV and wind plants at bus 33. The TD3 or DDPG agent sends residual corrections of the virtual inertia and damping to the VSG."));
C.push(...TABLE("nomen", "Nomenclature", ["Symbol", "Meaning", "Symbol", "Meaning"], [
  ["H_v, D_v", "Virtual inertia constant (s) and damping (pu) of the VSG", "H_d, D_d", "Diesel inertia constant and damper damping"],
  ["Δω_d, Δω_v, Δω_b", "Diesel, virtual and inertia-weighted rotor speed deviations (pu)", "Δf_m", "Measured (filtered) frequency deviation"],
  ["|Δf|max", "Maximum frequency deviation of an episode (nadir for load increases, overshoot for rejections)", "RoCoF", "Rate of change of frequency, max over a 100 ms window"],
  ["K_d, K_s", "Synchronising coefficients of diesel and VSG", "E′_q, E_v", "Diesel transient EMF and VSG EMF"],
  ["P_set", "VSG power set-point (secondary control)", "h", "BESS headroom in the direction of the deviation"],
  ["H̄, D̄", "Headroom-projected upper bounds of H_v, D_v", "a", "Residual action of the agent, a ∈ [−1, 1]²"],
  ["R_{n,g}", "Return of scenario n under grid setting g", "G_scen, G_event", "Scenario-level and event-wise oracle gains"],
  ["m_Q", "Q–V droop of the VSG (pu/pu)", "k_f, f_db", "Frequency droop and deadband of PV and wind"],
], [1300, 3500, 1300, 3539]));
C.push(P(`The plant ratings of the authors' single-bus study ${cite("khanIrea")} are scaled by k = 3.715/0.8 = 4.644 so that the peak load equals the published total, and the system base is scaled by the same factor (S`, { t: "b", sub: true }, ` = 9.2875 MVA), which keeps every per-unit parameter unchanged. These ratings are therefore a choice of the authors, not published values (${tref("plant")}). The diesel machine is the 4.9 MVA, 11 kV, 1500 rpm salient-pole alternator of Mahtani et al. ${cite("mahtani")} (3.92 MW at 0.8 power factor) with an IEEE 421.5 Type AC8C digital excitation system and its sample data ${cite("ieee4215")}.`));
C.push(P(`The operating points are taken from measured 2024 data for Nakhon Ratchasima, Thailand: hourly ERA5 wind at 100 m ${cite("era5")}, converted with an IEC class III power curve ${cite("iec61400")}, hourly NASA POWER irradiance and temperature ${cite("power")}, and the hourly demand of the Northeast region of Thailand from the EGAT system data ${cite("egat")}, scaled to the published peak of 3.715 MW. Within each 30 s episode the wind fluctuates around its hourly mean (turbulence intensity 10 %) and the load carries 0.5 % noise. The year is split into weekly blocks, five weeks for training, one for validation and one for testing in every seven, so that every season appears in every subset and whole weeks separate them.`));
C.push(...TABLE("plant", "Plant and control parameters, their basis and source", ["Item", "Value", "Basis", "Source"], [
  ["Feeder", "IEEE 33-bus, 12.66 kV, 32 lines + 5 open ties, 3.715 MW + j2.30 Mvar", "Published", `${cite("baran", "matpower")}`],
  ["Diesel alternator", "4.9 MVA, 11 kV, 1500 rpm; X_d 2.18, X_q 0.950, X′_d 0.286 pu; T′_do 4.0 s", "Published", `${cite("mahtani")}, Table II`],
  ["Diesel excitation", "IEEE 421.5 Type AC8C, sample data (K_PR 80, K_IR 5, K_DR 10, T_E 1.2 s, …)", "Standard", `${cite("ieee4215")}, Table H.18`],
  [HL("Diesel inertia"), HL("H_d = 2 s (own base)"), HL("Literature range"), HL(`0.1–2 s for diesel units ${cite("liu")}`)],
  ["Diesel governor and AGC", "Droop 5 %, T_g 0.2 s, T_e 0.5 s, ramp 1 pu/s, K_i 2.0, 15 % spinning reserve", "Authors (as in " + cite("khanIrea") + ")", `Model structure ${cite("kundur")}`],
  ["System base", "S_b = 9.2875 MVA (2 MVA × k), f_0 = 50 Hz", "Authors (scaling)", cite("khanIrea")],
  ["BESS (grid-forming VSG)", "2.32 MW / 9.29 MWh; η 0.95; SoC 0.10–0.95; H_v 0.2–8 s; D_v 0–50 pu", "Authors (scaled)", cite("khanIrea")],
  ["PV and wind", "PV 3.715 MW, de-loaded by 15 %; wind 4.644 MW, IEC class III, 100 m hub", "Authors (scaled)", `${cite("khanIrea", "iec61400")}`],
  ["VSG voltage control", "Q–V droop m_Q = 0.05 pu/pu; reactive capability 44 %", "Specification", `${cite("unifi")}, Table 7; ${cite("narang")}`],
  ["PV and wind frequency support", "Droop 5 %, deadband 0.06 %, open-loop response time 5 s", "Standard defaults", `${cite("ieee1547", "opender")}`],
  ["PV and wind volt-var", "V 0.92/0.98/1.02/1.08 pu, Q ±0.44 pu, response time 5 s", "Standard defaults", `${cite("ieee1547", "opender")}`],
  ["Load steps", "0.93–1.86 MW (25–50 % of peak), 2–3 per episode", "Authors (scaled)", cite("khanIrea")],
  ["Load and weather", "EGAT Northeast demand scaled to 3.715 MW; ERA5 wind; NASA POWER solar, 2024", "Measured", `${cite("egat", "era5", "power")}`],
  ["Frequency band and RoCoF limit", "±0.2 Hz; 1 Hz/s", "Grid code", `${cite("soguide", "rocof")}`],
  ["Reward weights", "Eq. (11); w_f 1.0, w_r 0.5, w_fast 2.0, w_b 0.1, …", "Authors (as in " + cite("khanIrea") + ")", "Sensitivity in Section VI.6"],
], [1900, 3700, 1500, 2539], "Basis: Published / Standard / Specification / Grid code / Measured: taken from the source; Authors: chosen or scaled by the authors; Literature range: within a range reported for this class of machine (yellow: no value for this machine)."));

C.push(H2("Dynamic Model"));
C.push(P(`The model is a phasor (RMS) model integrated with a 2 ms step. At every step the network equations (1) are solved for the bus voltages V, with the diesel represented by its transient EMF E′`, { t: "q", sub: true }, ` behind the salient-machine reactances and the VSG by its EMF E`, { t: "v", sub: true }, `∠θ`, { t: "v", sub: true }, ` behind X`, { t: "v", sub: true }, ` = 1/K`, { t: "s", sub: true }, ` = 0.5 pu; loads are constant power with the published P and Q at every bus, and the PV and wind plants are current injections at bus 33. The constant-power loads make (1) implicit in V; it is iterated to convergence within each step.`));
C.push(EQ("B1"));
C.push(P("The diesel rotor, field and governor follow (2)–(4), with the AC8C excitation of [" + (order.indexOf("ieee4215") + 1) + "] supplying E", { t: "fd", sub: true }, " and the automatic generation control (AGC) restoring the frequency:"));
C.push(EQ("B2"));
C.push(EQ("B3"));
C.push(EQ("B4"));
C.push(P(`The VSG emulates (5); its power set-point P`, { t: "set", sub: true }, ` takes part in secondary control, and its EMF follows the Q–V droop (6) of the UNIFI specification ${cite("unifi")}. When the requested power exceeds the state-of-charge (SoC) dependent BESS limits, the converter is current-limited and the virtual rotor is held at the limit.`));
C.push(EQ("B5"));
C.push(EQ("B6"));
C.push(P(`The frequency used by every controller, the reward and the metrics is the inertia-weighted rotor speed (7), filtered with T`, { t: "f", sub: true }, ` = 20 ms; RoCoF is its derivative and the reported maximum RoCoF is taken over a 100 ms window. The PV and wind plants add the IEEE 1547-2018 frequency droop (8) on their nameplate power P`, { t: "np", sub: true }, `: the PV plant up to its de-loaded reserve and the wind plant, which runs at maximum power, only downwards; the first-order lag τ reproduces the 5 s open-loop response time as in OpenDER ${cite("opender")}.`));
C.push(EQ("B7"));
C.push(EQ("B8"));
C.push(P(`Each operating point is dispatched as in ${cite("khanIrea")}: the renewable output is used first, the diesel runs between 30 % and 85 % of its rating, and a rule-based energy management system charges the BESS from surplus and discharges it above an economic diesel loading. An adequacy screen keeps only operating points whose upward reserve covers the largest load increase of the episode; none of the 200 test scenarios was screened out. With the tuned VSG the bus voltages stay between ${f3(VOLT.tuned_min)} and ${f3(VOLT.tuned_max)} pu in the validation scenarios of Section V.3 (${f3(VOLT.all_min)}–${f3(VOLT.all_max)} pu over all settings of the oracle grid); they are not part of the objective.`));

// =================================================================== IV. LEARNING PROBLEM
C.push(H1("IV. Learning Problem"));
C.push(H2("Episodes, Observations and Actions"));
C.push(P(`An episode lasts 30 s and contains two or three load steps. The first occurs between 0.5 and 1.5 s, the others at least 7 s apart and not in the last 5 s; each step is 0.93–1.86 MW (0.2–0.4 MW × k), is a load increase with probability 0.75 and a load rejection otherwise, and the net change stays within ±1.86 MW. The steps are distributed over the buses in proportion to the published loads. State of charge, AGC state and BESS set-point carry over from one event to the next, so that the controller must leave headroom for the following event. Of the 200 test scenarios, 109 contain two events and 91 three.`));
C.push(P(`The agent acts every 50 ms (600 decisions per episode). It observes 16 normalised quantities: frequency deviation, RoCoF, VSG power, rotor speed difference, upward and downward BESS headroom, PV reserve, SoC, wind and PV power, diesel power and spare capacity, pre-event load and the previously applied (H`, { t: "v", sub: true }, `, D`, { t: "v", sub: true }, `, α). It receives no information about a coming event. The action a ∈ [−1, 1]`, { t: "2", sup: true }, ` is residual ${cite("silver")}: a = 0 reproduces the tuned fixed VSG (H`, { t: "0", sub: true }, ` = 3 s, D`, { t: "0", sub: true }, ` = 10 pu, Section V), and ±1 move the parameter to its bounds, (9) for H`, { t: "v", sub: true }, ` and likewise for D`, { t: "v", sub: true }, `. The output layer of the actor is initialised at zero, so the untrained policy is exactly the tuned VSG.`));
C.push(EQ("B9"));
C.push(P(`The upper bounds come from the headroom projection (10) of ${cite("khanIrea")}: the damping power at the edge of the frequency band and the inertial power at the RoCoF limit must both fit in the BESS headroom h in the direction of the current deviation (Δf`, { t: "band", sub: true }, ` = 0.2 Hz, RoCoF`, { t: "lim", sub: true }, ` = 1 Hz/s). Every controller passes its parameters through the same first-order rate limit (τ = 0.25 s), as a real VSG does.`));
C.push(EQ("B10"));
C.push(H2("Reward"));
C.push(P(`The reward (11), averaged over the 25 integration steps of a decision, penalises the frequency deviation outside the ±0.2 Hz band ${cite("soguide")} and the RoCoF above 1 Hz/s, the fast VSG power above its secondary set-point (the response that H`, { t: "v", sub: true }, ` and D`, { t: "v", sub: true }, ` control), the total BESS power, the time at the converter limit s, the fraction ν of the decision spent beyond 1 Hz or 1 Hz/s, and the change and the size of the residual action. The weights are those of ${cite("khanIrea")} (w`, { t: "f", sub: true }, ` 1.0, w`, { t: "r", sub: true }, ` 0.5, w`, { t: "fast", sub: true }, ` 2.0, w`, { t: "b", sub: true }, ` 0.1, w`, { t: "s", sub: true }, ` 2.0, w`, { t: "v", sub: true }, ` 1.0, w`, { t: "Δ", sub: true }, ` 0.3, w`, { t: "a", sub: true }, ` 0.05, plus 0.02 on the in-band deviation); they were fixed before any 33-bus experiment and their influence is examined in Section VI.6. A deviation above 3 Hz ends the episode with a penalty of 50. The two action terms only regularise training; the return of an episode, the single objective on which every controller is tuned, selected and compared, is the sum of the other terms.`));
C.push(EQ("B11"));
C.push(H2("TD3 and DDPG"));
C.push(P(`TD3 ${cite("fujimoto")} and DDPG ${cite("lillicrap")} share one implementation: DDPG is TD3 with the twin critics, the target-policy smoothing and the delayed actor update switched off, so the comparison isolates these three ingredients. ${tref("learn")} lists the settings. Each run trains for 1000 episodes (600 000 decisions); every 50 episodes the deterministic policy is evaluated on 20 fixed validation scenarios and the best checkpoint is kept, the untrained policy (episode 0) included. A checkpoint is therefore never worse on validation than the VSG it starts from.`));
C.push(...TABLE("learn", "Learning settings (identical for TD3 and DDPG)", ["Setting", "Value"], [
  ["Actor and critic", "2 × 256 ReLU, tanh output; actor output layer initialised at zero"],
  ["Learning rates (actor / critic)", "1 × 10⁻⁴ / 3 × 10⁻⁴ (Adam)"],
  ["Discount, target update", "γ = 0.99, τ = 0.005"],
  ["Batch, replay buffer, warm-up", "256, 10⁶, 10 000 random steps"],
  ["Updates", "one gradient step every two environment steps"],
  ["Exploration", "Gaussian, σ 0.10 → 0.03 (linear over training)"],
  ["TD3 only", "Twin critics, target smoothing σ 0.2 (clip 0.5), actor delay 2"],
  ["Budget", "1000 episodes × 5 seeds (0–4) per algorithm"],
  ["Checkpoint selection", "Best mean return on 20 fixed validation scenarios, every 50 episodes"],
], [3800, 5839]));

// =================================================================== V. BENCHMARK PROTOCOL
C.push(H1("V. Benchmark Protocol"));
C.push(H2("Baselines and Their Tuning"));
C.push(P(`Five non-learning controllers are compared. The fixed VSG keeps (H`, { t: "v", sub: true }, `, D`, { t: "v", sub: true }, `) constant; its untuned version uses the nominal values of the single-bus study (3 s, 20 pu). The bang-bang controller of Alipoor et al. ${cite("alipoor")} switches between a large and a small inertia depending on whether the rotor is accelerating away from or towards nominal speed. The RoCoF-adaptive controller raises H`, { t: "v", sub: true }, ` with |RoCoF| and D`, { t: "v", sub: true }, ` with |Δf|. The direction-aware controller follows the principle of Li et al. ${cite("li17")}: inertia is added only while the deviation is growing (Δf·RoCoF > 0) and damping grows with |Δf|. The fuzzy controller is a zero-order Sugeno scheduler ${cite("sugeno")} with three triangular sets (negative, zero, positive) on Δf/Δf`, { t: "band", sub: true }, ` and RoCoF/RoCoF`, { t: "lim", sub: true }, `; it adds inertia when both inputs have the same sign, removes it when they differ, and adds damping in proportion to the frequency membership. `, TODO("the fuzzy rule base is generic; replace it by a published rule table if available, and check the direction-aware rule against Li et al. [" + (order.indexOf("li17") + 1) + "]")));
C.push(P(`All baselines are tuned by grid search on 40 validation scenarios, with the return as the objective. The fixed VSG is tuned first over H`, { t: "v", sub: true }, ` ∈ {1, 3, 5, 8} s and D`, { t: "v", sub: true }, ` ∈ {5, 10, 15, 20, 25, 30, 40, 50} pu; the adaptive rules are then tuned around the best fixed setting, which is also the centre of the residual RL policy (bang-bang: 9 settings; RoCoF-adaptive: 24; direction-aware: 20; fuzzy: 20 gain pairs, each including zero gain). The best fixed setting is H`, { t: "v", sub: true }, ` = 3 s, D`, { t: "v", sub: true }, ` = 10 pu (validation return ${f2(GRID.best)}); over the ${GRID.n} fixed settings the return ranges from ${f2(GRID.worst)} to ${f2(GRID.best)} (median ${f2(GRID.median)}), and the untuned setting scores ${f2(GRID.H3D20)}, i.e. better than the median setting. For all three adaptive rules the best gains are zero: on validation every non-zero adaptation improved the maximum deviation but cost more in BESS power than it saved, so the tuned rules coincide with the tuned fixed VSG.`));
C.push(P(`The learning agents act under the headroom projection (10), while the fixed VSG and the rules do not. The fixed VSG is therefore also evaluated with the projection applied ("fixed + projection"). This controller is exactly the untrained RL policy and is the reference against which the effect of learning is measured; the unprojected fixed VSG is reported as well because it is the controller a practitioner would deploy without a feasibility layer.`));
C.push(H2("Test Set and Statistics"));
C.push(P(`Every controller and every seed is evaluated on the same 200 test scenarios drawn from the test weeks, which were not used in training, checkpoint selection or tuning. The maximum frequency deviation |Δf|`, { t: "max", sub: true }, ` of an episode is its nadir for load increases and its overshoot for load rejections. For the learning methods the metrics are first averaged over the five seeds for each scenario, so that each scenario is one paired observation; seed-level results are reported separately (${tref("seed")}). Means are given with 95 % percentile-bootstrap intervals over scenarios ${cite("efron")}. TD3 is compared with every other controller on eight metrics by the Wilcoxon signed-rank test ${cite("wilcoxon")} on the paired differences, and the p-values of all 64 comparisons are corrected together with the Holm procedure ${cite("holm")}.`));
C.push(H2("Oracle Bounds and Convergence"));
C.push(P(`The oracles use a grid of 24 settings (H`, { t: "v", sub: true }, ` ∈ {1, 3, 5, 8} s × D`, { t: "v", sub: true }, ` ∈ {5, 10, 15, 20, 30, 50} pu) on 20 validation scenarios. The scenario-level gain G`, { t: "scen", sub: true }, ` in (12) compares the best setting chosen separately for each scenario with the best single setting for all of them. The event-wise gain G`, { t: "event", sub: true }, ` lets the setting change at every load step, with hindsight of the events; it is found per scenario by coordinate descent over the segments, starting from the best single setting, and is therefore a lower estimate of the event-wise optimum. Both are bounds for piecewise-constant schedules on the grid: a policy that changes its parameters continuously, or uses values between grid points, could in principle exceed them. Their uncertainty is given by 95 % bootstrap intervals over the scenarios.`));
C.push(EQ("B12"));
C.push(P(`To show how the bound depends on the plant, G`, { t: "scen", sub: true }, ` is also computed for twelve sizings: BESS power of 0.25, 0.625 (published plant) and 1.0 times the peak load (four-hour energy), diesel ratings of 2.45 and 4.9 MVA with the same per-unit machine data, and load steps of half and full size; and for five weightings of the objective (Section VI.6). Convergence of each training run is tested on the validation curve: an ordinary least-squares slope over the last quarter of training that is not significantly different from zero (two-sided t-test, p ≥ 0.05) is a plateau. The closeness to the optimum is measured by the gap closed (13) between the best fixed setting and the oracle on the validation scenarios, and the seeds are summarised by the interquartile mean (IQM) with a bootstrap interval ${cite("agarwal")}.`));
C.push(EQ("B13"));

// =================================================================== VI. RESULTS
C.push(H1("VI. Results"));
C.push(H2("Comparison on the Test Set"));
const row = (c, name) => {
  const t = T[c], sr = N.seed_return[c];
  const ret = `${f2(t.return[0])} [${f2(t.return[1])}, ${f2(t.return[2])}]` + (sr.length > 1 ? ` (±${f2(sd(sr))})` : "");
  return [name, ret, f3(t.nadir_hz[0]), f3(t.rocof_max_hz_s[0]), f2(t.settling_time_s[0]), f3(t.bess_energy_kwh[0]), f2(t.infeasible_commit_s[0]), `${f1(100 * t.rocof_violation[0])}`];
};
C.push(...TABLE("test", "Test-set results (200 scenarios; learning methods: mean of 5 seeds)",
  ["Controller", "Return [95 % CI] (±seed s.d.)", "|Δf|max (Hz)", "Max RoCoF (Hz/s)", "Settling (s)", "BESS energy (kWh)", "Infeasible commitment (s)", "RoCoF > 1 Hz/s (% of scen.)"],
  [row("fixed", "Fixed VSG, untuned"), row("fixed_tuned", "Fixed VSG, tuned"), row("fixed_feasible", "Fixed VSG + projection"),
   row("bang_bang", "Bang-bang, tuned"), row("adaptive_rocof", "RoCoF-adaptive, tuned"), row("adaptive_dir", "Direction-aware, tuned"),
   row("fuzzy", "Fuzzy, tuned"), row("ddpg", "DDPG"), row("td3", "TD3")],
  [1900, 2050, 800, 850, 800, 850, 1000, 1000],
  "Return: higher is better. Infeasible commitment: time per episode in which the declared H_v, D_v need more power than the BESS headroom can deliver. No scenario collapsed under any controller; |Δf| exceeded 1 Hz in 1.5 % of the scenarios under every controller."));
C.push(P(`${tref("test")} summarises the test results. Tuning alone moves the fixed VSG from a return of ${f2(T.fixed.return[0])} to ${f2(T.fixed_tuned.return[0])}, an improvement of ${f1(gainUntuned)} %. The untuned setting (D`, { t: "v", sub: true }, ` = 20 pu) gives the smallest frequency deviation of all controllers, ${f3(T.fixed.nadir_hz[0])} Hz, but uses ${f1(pct(T.fixed.bess_energy_kwh[0], T.fixed_tuned.bess_energy_kwh[0]))} % more BESS energy; the objective rewards supporting the frequency only as much as the band requires, and the tuned setting does that with less damping. The three adaptive rules coincide with the tuned fixed VSG because their tuned gains are zero, and the bang-bang rule lowers the deviation and the RoCoF slightly at a higher BESS energy, ending marginally below the tuned fixed VSG. The headroom projection costs the fixed VSG ${f2(T.fixed_tuned.return[0] - T.fixed_feasible.return[0])} in return and removes almost all infeasible commitments (from ${f2(T.fixed_tuned.infeasible_commit_s[0])} s to ${f2(T.fixed_feasible.infeasible_commit_s[0])} s per episode), in agreement with ${cite("khanIrea")}.`));
C.push(P(`Neither learning method improves the return over its own starting controller, the fixed VSG with projection (${f2(T.fixed_feasible.return[0])}): TD3 reaches ${f2(T.td3.return[0])} (paired difference ${f2(PD("td3_vs_fixed_feasible", "return").mean_diff)}, Holm p = ${f2(H("fixed_feasible", "return")[3])}) and DDPG ${f2(T.ddpg.return[0])}. ${tref("seed")} explains the averages. For two TD3 seeds and four DDPG seeds the best validation checkpoint was the untrained policy, so these seeds are identical to the starting controller on every test scenario. The remaining TD3 seeds change the return by ${N.seed_vs_base.td3_s0.mean_diff >= 0 ? "+" : ""}${f2(N.seed_vs_base.td3_s0.mean_diff)}, ${f2(N.seed_vs_base.td3_s2.mean_diff)} and ${f2(N.seed_vs_base.td3_s4.mean_diff)}, none significantly; the remaining DDPG seed loses ${f2(-N.seed_vs_base.ddpg_s0.mean_diff)} (p = ${pe(N.seed_vs_base.ddpg_s0.p)}). The validation gains that made these checkpoints the best ones, up to 1.6 %, did not carry over to unseen weeks.`));
const sv = N.seed_vs_base;
const seedRow = (algo, s) => { const k = `${algo}_s${s}`, r = sv[k]; return [`${algo.toUpperCase()} seed ${s}`, f2(N.seed_return[algo][s]), r.identical ? "0 (identical)" : `${r.mean_diff >= 0 ? "+" : ""}${f2(r.mean_diff)}`, r.identical ? "–" : pe(r.p)]; };
C.push(...TABLE("seed", "Test return of every seed against the starting controller (fixed VSG + projection, return " + f2(T.fixed_feasible.return[0]) + ")",
  ["Run", "Test return", "Mean paired difference", "Wilcoxon p (raw)"],
  [0, 1, 2, 3, 4].map((s) => seedRow("td3", s)).concat([0, 1, 2, 3, 4].map((s) => seedRow("ddpg", s))), [2600, 2300, 2400, 2339],
  "Identical: the validation-selected checkpoint is the untrained policy (episode 0)."));
C.push(...FIGURE("paired", "fig_test_paired.png", 6.4, "Paired differences to the tuned fixed VSG on the 200 test scenarios (learning methods averaged over five seeds per scenario). Boxes: interquartile range, whiskers: 5–95 % without outliers, diamonds: means. The adaptive rules are not shown because they coincide with the tuned fixed VSG."));
C.push(H2("Paired Tests: What TD3 Changes"));
const sigRows = [["fixed_tuned", "Fixed VSG, tuned"], ["fixed_feasible", "Fixed VSG + projection"], ["bang_bang", "Bang-bang"], ["ddpg", "DDPG"], ["fixed", "Fixed VSG, untuned"]].map(([k, name]) => {
  const cellv = (m) => { const h = H(k, m); return `${h[0] >= 0 ? "+" : ""}${m === "return" || m === "settling_time_s" ? f2(h[0]) : f3(h[0])} / ${Math.round(100 * h[1])} % / ${pe(h[3])}`; };
  return [name, cellv("return"), cellv("nadir_hz"), cellv("rocof_max_hz_s"), cellv("settling_time_s"), cellv("bess_energy_kwh")];
});
C.push(...TABLE("paired", "TD3 against each controller: median paired difference / share of scenarios in which TD3 is better / Holm-adjusted p", ["TD3 vs", "Return", "|Δf|max (Hz)", "Max RoCoF (Hz/s)", "Settling (s)", "BESS energy (kWh)"],
  sigRows, [1900, 1550, 1550, 1550, 1550, 1539],
  "Differences are TD3 minus the other controller; for return higher is better, for all other metrics lower is better. The RoCoF-adaptive, direction-aware and fuzzy rows equal the tuned fixed VSG row. Holm correction over all 64 comparisons."));
const hTun = (m) => H("fixed_tuned", m);
C.push(P(`${tref("paired")} shows that TD3 does change the response, only not in the direction of the objective. Against the tuned fixed VSG it lowers |Δf|`, { t: "max", sub: true }, ` by a median of ${f3(-hTun("nadir_hz")[0])} Hz and does so in ${Math.round(100 * hTun("nadir_hz")[1])} % of the scenarios (Holm-adjusted p = ${pe(hTun("nadir_hz")[3])}), a ${f1(nadirRed)} % smaller mean. It pays for this with a higher maximum RoCoF (median +${f3(hTun("rocof_max_hz_s")[0])} Hz/s, p = ${pe(hTun("rocof_max_hz_s")[3])}) and a slower settling (median +${f2(hTun("settling_time_s")[0])} s, p = ${pe(hTun("settling_time_s")[3])}), with an unchanged BESS energy; the net effect on the return is not significant. ${fref("traces")} illustrates the mechanism on the test scenario with the largest first-event load rejection, which the evaluation script selects automatically before any result is seen: after the first event TD3 lowers the virtual inertia and damping, which reduces the overshoot of that event from about 0.53 Hz to 0.35 Hz, but after the second event it drives the damping almost to zero, so that the deviation stays outside the band for longer than under the fixed VSG.`));
C.push(P(`Against DDPG, TD3 has the better return in ${Math.round(100 * H("ddpg", "return")[1])} % of the scenarios (raw p = ${pe(H("ddpg", "return")[2])}), which is not significant after the Holm correction (p = ${f2(H("ddpg", "return")[3])}), and the lower deviation in ${Math.round(100 * H("ddpg", "nadir_hz")[1])} % of them (p = ${pe(H("ddpg", "nadir_hz")[3])}). Against the untuned fixed VSG, TD3 improves the return in every scenario (median +${f2(H("fixed", "return")[0])}, p = ${pe(H("fixed", "return")[3])}), a ${f1(gainTd3Untuned)} % improvement, while that VSG has the smaller deviation. The 20 % figure depends on the untuned setting; because this setting is better than the median of the tuning grid, a randomly chosen untuned setting would usually make learning look even better.`));
C.push(...FIGURE("traces", "fig_traces.png", 6.4, `Test scenario ${N.trace_scenario} (largest first-event load rejection): load rejection of 1.80 MW at 0.8 s, load increases of 1.05 MW at 8.2 s and 1.00 MW at 22.5 s. Frequency deviation (grey band: ±0.2 Hz), BESS power (positive: discharge), and the virtual inertia and damping applied by the tuned fixed VSG, DDPG (seed 0) and TD3 (seed 0).`));
C.push(H2("Training Convergence"));
C.push(P(`${fref("conv")} shows the validation return during training. All five TD3 runs reached a plateau over the last quarter of training; of the DDPG runs, three reached a plateau, one was still improving and one was degrading (${tref("conv")}). On the validation scenarios the best fixed setting scores ${f2(conv.td3.R_best_fixed)} and the per-scenario oracle ${f2(conv.td3.R_oracle)}, a margin of ${f2(pct(conv.td3.R_oracle, conv.td3.R_best_fixed))} %. The selected TD3 checkpoints closed on average ${f2(conv.td3.mean_gap_closed_best)} of this margin and the selected DDPG checkpoints ${f2(conv.ddpg.mean_gap_closed_best)}; at the end of training both had fallen below the fixed setting (gap closed ${f1(conv.td3.mean_gap_closed_final)} and ${f1(conv.ddpg.mean_gap_closed_final)}), DDPG much further than TD3. The IQM of the final validation return is ${f2(conv.td3.iqm_final)} [${f2(conv.td3.iqm_ci_low)}, ${f2(conv.td3.iqm_ci_high)}] for TD3 and ${f2(conv.ddpg.iqm_final)} [${f2(conv.ddpg.iqm_ci_low)}, ${f2(conv.ddpg.iqm_ci_high)}] for DDPG. The clearest difference between the two algorithms is therefore stability: the twin critics, target smoothing and delayed updates of TD3 keep its policies close to the starting controller, whereas DDPG drifts away from it.`));
C.push(...FIGURE("conv", "fig_convergence_paper.png", 6.4, "Validation return during training (grey: individual seeds; colour: mean of five seeds; shaded: last quarter used for the plateau test). Horizontal lines: best fixed setting and per-scenario oracle on the same validation scenarios."));
C.push(...TABLE("conv", "Convergence of the training runs (validation scenarios)", ["Run", "Verdict", "Slope (per 100 ep.)", "p", "Best return (episode)", "Final return", "Gap closed, best / final"],
  convSeeds.map((r) => [`${r.run.toUpperCase()} ${r.seed}`, r.verdict.replace(" (plateau)", ""), f2(r.slope_per_100_ep), f3(r.p_slope),
    `${f2(r.val_return_best)} (${r.best_at_episode})`, f2(r.val_return_final), `${f2(r.gap_closed_best)} / ${f1(r.gap_closed_final)}`]),
  [1250, 1550, 1200, 900, 1700, 1300, 1739], "The untrained policy (episode 0) scores −47.97 on these scenarios; a best return of −47.97 at episode 0 means training never improved on it."));
C.push(H2("Hyperparameter Screen"));
const hpRow = (h, name) => [name, f2(hp[`td3_${h}`].best), f2(hp[`td3_${h}`].final), f2(hp[`ddpg_${h}`].best), f2(hp[`ddpg_${h}`].final)];
C.push(P(`To check that the settings of ${tref("learn")} do not favour one algorithm, both were trained with four settings for 500 episodes and two seeds each (${tref("hp")}): the settings above, the defaults of the TD3 authors' code, the learning rates of the DDPG paper, and doubled exploration noise. No DDPG run improved on its starting policy under any setting, and only two of the eight TD3 runs did, by at most ${f2(Math.abs(pct(-47.639, -47.970)))} % on validation. Under every setting the final DDPG policies were worse than the final TD3 policies. With two seeds and half the training budget the screen is a plausibility check rather than a full tuning, but it gives no indication that other hyperparameters would change the conclusion.`));
C.push(...TABLE("hp", "Hyperparameter screen: mean validation return of two seeds (500 episodes)", ["Setting (actor lr / critic lr / noise)", "TD3 best", "TD3 final", "DDPG best", "DDPG final"],
  [hpRow("h0", "1e-4 / 3e-4 / 0.10 (" + tref("learn") + ")"), hpRow("h1", "3e-4 / 3e-4 / 0.10 (TD3 code defaults " + cite("fujimoto") + ")"),
   hpRow("h2", "1e-4 / 1e-3 / 0.10 (DDPG paper " + cite("lillicrap") + ")"), hpRow("h3", "1e-4 / 3e-4 / 0.20")],
  [3800, 1450, 1450, 1450, 1489], "Starting policy: −47.97."));
C.push(H2("How Much Could Adaptation Gain?"));
const ocN = OCI["event_nominal"], ocR = OCI["event_most_room"];
C.push(P(`The oracle bounds of ${fref("oracle")} explain why no controller improved on the tuned fixed VSG. On the published plant the best setting per scenario improves the return by only ${f2(omNom.oracle_gain_pct)} % (95 % interval ${ci([0, ocN[1], ocN[2]])} %) over the best single setting, and switching the setting at every event raises this to ${f2(evNom.event_gain_pct)} % (${ci([0, ocN[4], ocN[5]])} %), with a gain above 1 % in ${evNom.scen_event_gt_1pct} of 20 scenarios. These bounds use knowledge of the coming events; a causal controller must infer the event from its first milliseconds and can capture only part of them. Over the twelve sizings the scenario-level bound ranges from ${f2(Math.min(...N.oracle_map.map((r) => r.oracle_gain_pct)))} % to ${f2(omMax.oracle_gain_pct)} %. The largest value occurs with the smallest BESS and diesel (0.25 × peak load, 2.45 MVA) and full-size events, where ${Math.round(100 * omMax.screen_rejected_frac)} % of the operating points fail the adequacy screen and ${Math.round(100 * omMax.collapse_frac_best)} % of the remaining scenarios collapse under the best fixed setting, i.e. outside the practical operating range; its interval is also the widest (${ci(OCI["0.25/2.45/1"])} %). In the practical condition with the largest bound (BESS 1.0 × peak load, 4.9 MVA diesel, half-size events) the event-wise bound reaches ${f2(evRoom.event_gain_pct)} % (${ci([0, ocR[4], ocR[5]])} %), but the returns there are an order of magnitude smaller (best fixed ${f2(evRoom.R_best_fixed)} against ${f2(evNom.R_best_fixed)} on the published plant), so the absolute gain per episode (${f2(evRoom.R_event_oracle - evRoom.R_best_fixed)}) is smaller than on the published plant (${f2(evNom.R_event_oracle - evNom.R_best_fixed)}).`));
C.push(...FIGURE("oracle", "fig_oracle.png", 6.4, "Oracle bounds on validation scenarios (20 per condition). (a) Scenario-level gain over the best fixed setting for twelve plant sizings (dark: published plant). (b) Scenario-level and event-wise gains on the published plant and on the practical condition with the largest scenario-level gain (BESS 1.0 × peak, 4.9 MVA diesel, half-size events)."));
C.push(H2("Sensitivity to the Reward Weights"));
const wName = { base: "Weights of this paper", freq_x5: "Frequency deviation × 5", rocof_x5: "RoCoF × 5", storage_div5: "BESS and fast VSG power ÷ 5", storage_x5: "BESS and fast VSG power × 5" };
C.push(P(HL(`Because the objective weights were taken from the single-bus study, the scenario-level oracle was recomputed under four other weightings, fixed before the computation (${tref("weights")}). The plant does not depend on the reward, so every cost component of every decision was recorded once and re-weighted. Under every weighting the bound stays small, at most ${f2(Math.max(...N.weights.map((r) => r.oracle_gain_pct)))} %. It is, however, smallest for the weights of this paper and for a heavier RoCoF penalty (${f2(WT.base.oracle_gain_pct)} % and ${f2(WT.rocof_x5.oracle_gain_pct)} %) and grows to ${f2(WT.freq_x5.oracle_gain_pct)} % (${ci([0, WT.freq_x5.gain_ci_lo, WT.freq_x5.gain_ci_hi])} %) when the frequency deviation weighs five times more and to ${f2(WT.storage_div5.oracle_gain_pct)} % (${ci([0, WT.storage_div5.gain_ci_lo, WT.storage_div5.gain_ci_hi])} %) when battery use weighs five times less. Under these frequency-focused objectives the best fixed setting moves to D_v = 20 pu and the setting of this paper ranks ${WT.freq_x5.rank_of_paper_setting}th and ${WT.storage_div5.rank_of_paper_setting}th of 24. The conclusion that the room for adaptation is small therefore holds for all weightings tested, but the weighting of this paper leaves the least room; whether a learner trained on a frequency-focused objective captures the 2–3 % that the oracle allows is left for future work.`)));
C.push(...TABLE("weights", "Scenario-level oracle bound under five weightings of the objective (20 validation scenarios)", ["Weighting", "Best fixed (H_v, D_v)", "Oracle gain [95 % CI]", "Rank of (3 s, 10 pu)"],
  N.weights.map((r) => [HL(wName[r.weighting]), HL(`${r.best_H} s, ${r.best_D} pu`), HL(`${f2(r.oracle_gain_pct)} % [${f2(Math.max(r.gain_ci_lo, 0))}, ${f2(r.gain_ci_hi)}]`), HL(`${r.rank_of_paper_setting} of 24`)]),
  [3600, 2000, 2200, 1839], "Each weighting multiplies the named terms of (11); all other weights unchanged."));
C.push(H2("Smaller Disturbances and the Value of Adaptation"));
const hR = (c) => HALF[c];
const hp2 = (k) => HP2[k].return;
C.push(P(`The full-size load steps (25–50 % of the peak load) exceed the 1 Hz/s RoCoF limit in ${f1(100 * T.fixed_tuned.rocof_violation[0])} % of the test scenarios under the tuned fixed VSG and in 80–87 % under every controller (${tref("test")}), which shows that they are severe for this plant. All controllers were therefore also tested, without retraining or re-tuning, on the same 200 test scenarios with half-size steps (${tref("half")}). With half-size steps the RoCoF limit is ${hR("fixed_tuned").rocof_violation === 0 ? "never exceeded" : `exceeded in ${f1(100 * hR("fixed_tuned").rocof_violation)} % of the scenarios`} under the tuned fixed VSG and is exceeded in at most ${f1(100 * Math.max(...Object.values(HALF).map((v) => v.rocof_violation)))} % under any controller.`));
C.push(P(`The smaller steps change the ranking. TD3, trained only on full-size steps, now beats the fixed VSG tuned for full-size steps by ${f2(hp2("td3_vs_fixed_tuned").mean_diff)} in return (${f1(pct(hR("td3").return, hR("fixed_tuned").return))} %, better in ${Math.round(100 * hp2("td3_vs_fixed_tuned").a_better_frac)} % of the scenarios, p = ${pe(hp2("td3_vs_fixed_tuned").p)}): it lowers the damping when the events are small, uses less BESS energy and accepts a larger deviation that stays inside the band. DDPG does not (${f2(hp2("ddpg_vs_fixed_tuned").mean_diff)}, p = ${f2(hp2("ddpg_vs_fixed_tuned").p)}). A fixed VSG re-tuned on half-size validation steps (H`, { t: "v", sub: true }, ` = 3 s, D`, { t: "v", sub: true }, ` = 5 pu), however, is better still: it beats TD3 by ${f2(-hp2("td3_vs_fixed_retuned").mean_diff)} (p = ${pe(hp2("td3_vs_fixed_retuned").p)}). TD3 thus recovers ${f1(100 * (hR("td3").return - hR("fixed_tuned").return) / (hR("fixed_retuned").return - hR("fixed_tuned").return))} % of the benefit of re-tuning without being retrained or re-tuned, which is the kind of value adaptive control can offer when the disturbance statistics change, but it does not reach a fixed VSG tuned for the new conditions.`));
C.push(...TABLE("half", "Test results with half-size load steps (200 scenarios; controllers not retrained)", ["Controller", "Return", "|Δf|max (Hz)", "Max RoCoF (Hz/s)", "BESS energy (kWh)", "RoCoF > 1 Hz/s (%)"],
  [["fixed_tuned", "Fixed VSG, tuned for full-size steps"], ["fixed_feasible", "Fixed VSG + projection"], ["bang_bang", "Bang-bang, tuned for full-size steps"],
   ["ddpg", "DDPG (5 seeds)"], ["td3", "TD3 (5 seeds)"], ["fixed_retuned", "Fixed VSG re-tuned for half-size steps"], ["fixed_retuned_feasible", "Re-tuned fixed VSG + projection"]].map(([k, n]) =>
    [n, f2(hR(k).return), f3(hR(k).nadir_hz), f3(hR(k).rocof_max_hz_s), f3(hR(k).bess_energy_kwh), f1(100 * hR(k).rocof_violation)]),
  [3300, 1200, 1200, 1300, 1300, 1339], "Re-tuning: grid search over the 32 fixed settings on 40 half-size validation scenarios."));

// =================================================================== VII. DISCUSSION
C.push(H1("VII. Discussion"));
C.push(P({ t: "Why the learned controllers did not win. ", b: true }, `The decisive quantity is the oracle bound, not the algorithm. When the best possible piecewise-constant scheduler gains 0.2–1.6 % over a well-tuned fixed VSG, the noise of selecting a checkpoint on 20 validation scenarios is of the same size as the prize, and the selected policies either reproduce the starting controller or trade one part of the objective for another. The adaptive rules behave the same way: tuned on the same objective, all of them chose zero gain. The result is consistent with the single-bus study ${cite("khanIrea")} and holds on a feeder with voltage dynamics and standard converter functions.`));
C.push(P({ t: "Why the literature reports large gains. ", b: true }, `Against the untuned fixed VSG, TD3 improves the objective by ${f1(gainTd3Untuned)} % with p < 10`, { t: "−30", sup: true }, `, a result that would read as a clear success. Tuning the fixed VSG on the same validation data delivers ${f1(gainUntuned)} % without any learning. A comparison against an untuned baseline therefore measures mostly the value of tuning. Two further practices widen the apparent gap: reporting the best of several seeds, and evaluating on the scenarios used for checkpoint selection. In this study the best validation result of a TD3 seed was 1.6 % above the starting policy, yet no seed was significantly better on the test weeks. We recommend that RL-for-VSG studies report a tuned fixed baseline, an oracle bound and test results on held-out data from several seeds ${cite("henderson", "agarwal")}.`));
C.push(P({ t: "Where learning does help. ", b: true }, `Two results point to the value of a learned scheduler. First, TD3 consistently lowers the maximum frequency deviation, by ${f1(nadirRed)} % against the tuned fixed VSG and rules and by ${f1(-pct(T.td3.nadir_hz[0], T.bang_bang.nadir_hz[0]))} % against the bang-bang rule, at the cost of RoCoF and settling time; whether this trade is desirable is a matter of the objective, and the reward sensitivity shows that frequency-focused objectives leave 2–3 % of room. This advantage is a few hundredths of a hertz, and in the single-bus study a nadir advantage of this size disappeared in a circuit-level model ${cite("khanIrea")}, so it should be confirmed at circuit level before it is claimed. Second, when the disturbances become smaller than in training, TD3 adapts without retraining and recovers about half of the benefit of re-tuning, which a fixed VSG cannot do; a fixed VSG re-tuned for the new conditions remains better. Learning is therefore most useful where re-tuning is impractical, for example when the disturbance statistics drift.`));
C.push(P({ t: "When could learning pay off? ", b: true }, `The oracle map identifies the conditions with more room: a small diesel unit, a small BESS and large events, i.e. weak systems close to their adequacy limit; the reward sensitivity adds frequency-focused objectives. In the practical range examined here the scenario-level bound stays below 4 %. A study that wishes to demonstrate the value of RL scheduling should first show such a bound for its plant and objective.`));

// =================================================================== VIII. LIMITATIONS
C.push(H1("VIII. Limitations"));
C.push(BUL({ t: "Diesel inertia. ", b: true }, HL(`The inertia constant of the published machine is not given in its source ${cite("mahtani")}; H_d = 2 s is the upper end of the 0.1–2 s range reported for diesel generators in ${cite("liu")}. A smaller value would make the system weaker and could enlarge the oracle bound.`)));
C.push(BUL({ t: "Model fidelity. ", b: true }, "The model is a phasor model with an ideal step-up transformer at the diesel terminal and without converter inner loops; the reaction delay of the IEEE 1547 functions is not modelled. A circuit-level (EMT) check was not repeated on the feeder. For the single-bus plant of ", cite("khanIrea"), ", whose machine, VSG and control models are reused here, a three-phase Simscape model followed the phasor model with an RMS frequency difference of 0.008–0.033 Hz over 12 test scenarios and changed the nadir of the tuned fixed VSG by 0.5 %, but the nadir advantage of TD3 disappeared and the RoCoF measured by the PLL over 100 ms was about 2.9 times higher. The conclusion that learning does not improve the objective is therefore expected to hold at circuit level, whereas the small nadir advantage of TD3 and the absolute RoCoF values are not."));
C.push(BUL({ t: "Design of the learner. ", b: true }, "The residual action, the zero-initialised actor, the penalty on the action size, the rate limit and checkpoint selection on 20 validation scenarios all keep the policy close to the tuned VSG. A less constrained learner was not trained. Because the oracle bounds every piecewise-constant schedule on the grid regardless of how it is produced, a less constrained learner could gain at most what the oracle allows unless it exploits continuous parameter changes."));
C.push(BUL({ t: "Objective and disturbances. ", b: true }, "All test conclusions refer to the reward (11) and to full-size steps; the oracle under other weightings and the half-size tests indicate how they change, but the learners were not retrained for either."));
C.push(BUL({ t: "Single feeder and site. ", b: true }, "One feeder, one year and one site are studied; the oracle map covers sizing, not topology."));

// =================================================================== IX. CONCLUSION
C.push(H1("IX. Conclusion"));
C.push(P(`On an islanded IEEE 33-bus feeder with a published diesel machine and exciter and standard converter functions, driven by measured load and weather, neither TD3 nor DDPG improved the control objective over the fixed VSG they started from, and four tuned adaptive rules reduced to the tuned fixed VSG. The reason is the size of the prize: a per-scenario oracle bounds the gain of any piecewise-constant scheduler at ${f2(omNom.oracle_gain_pct)} %, an event-wise oracle with hindsight at ${f2(evNom.event_gain_pct)} %, and no weighting of the objective tested raised the scenario-level bound above ${f2(Math.max(...N.weights.map((r) => r.oracle_gain_pct)))} %. TD3 was more stable than DDPG in training, reduced the maximum frequency deviation by ${f1(nadirRed)} % at the cost of RoCoF and settling time, and, when the disturbances became smaller than in training, adapted without retraining and recovered about half of the benefit of re-tuning. Against an untuned fixed VSG the same TD3 policies would have been reported as a ${f1(gainTd3Untuned)} % improvement. Benchmarks of learned VSG control should therefore include a tuned fixed baseline, an oracle bound and multi-seed results on held-out data.`));

// =================================================================== back matter
C.push(H1("Acknowledgements"));
C.push(P("This work was supported by the Vidhetbundit Scholarship, Suranaree University of Technology, Thailand. ", TODO("confirm funding statement")));
C.push(H1("Data and Code Availability"));
C.push(P("The code, configuration files, input data and the scripts that reproduce every table and figure are available at ", TODO("public GitHub URL or Zenodo DOI"), ". ERA5 data: Copernicus Climate Change Service; solar data: NASA POWER Project; load data: EGAT system data [", String(order.indexOf("egat") + 1), "]."));
C.push(H1("References"));
const REFP = [];
order.forEach((k, i) => {
  const m = REF[k].match(/^(.*?)( \[AUTHOR: [^\]]*\])?$/);
  const parts = [`[${i + 1}] `, m[1]];
  if (m[2]) parts.push({ t: m[2], hl: true });
  REFP.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 }, indent: { left: 340, hanging: 340 }, children: runs(parts, 16) }));
});
const unused = Object.keys(REF).filter((k) => !order.includes(k));
if (unused.length) throw new Error("references never cited: " + unused.join(", "));
C.push(...REFP);

const AI = (...parts) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100 }, children: runs(parts, 16) });
C.push(H1("Authors’ information"));
C.push(AI({ t: "1", sup: true }, "School of Electrical Engineering, Institute of Engineering, Suranaree University of Technology, 111 University Avenue, Suranaree Sub-district, Mueang Nakhon Ratchasima District, Nakhon Ratchasima 30000, Thailand."));
C.push(AI("Corresponding author: Anant Oonsivilai, E-mail: ", TODO("corresponding author e-mail")));
C.push(AI(TODO("insert a passport-size photograph before each biography")));
C.push(AI({ t: "Muhammad Binyameen Khan ", b: true }, "received his bachelor’s degree in Electrical Engineering from ISRA University, Islamabad, Pakistan, and is currently pursuing the M.Sc. degree in Electrical Engineering at Suranaree University of Technology, Thailand. ", TODO("complete as in the IREA manuscript")));
C.push(AI({ t: "Anant Oonsivilai ", b: true }, "received the B.Eng. degree in Electrical Engineering from Khon Kaen University, Thailand, the M.Eng. degree in Electrical Engineering from King Mongkut’s University of Technology North Bangkok, Thailand, and the Ph.D. degree in Electrical and Computer Engineering from Dalhousie University, Canada. He is an Associate Professor at Suranaree University of Technology. ", TODO("complete as in the IREA manuscript")));

// ---------- title block ----------
const CHECK = [
  "Diesel inertia H_d = 2 s: check the 0.1–2 s range in Liu et al. (IET Energy Syst. Integr., 2024, doi 10.1049/esi2.12099, open access) and keep or replace the citation (Table IV, Section VIII).",
  "Related work (Section II, Table I): check every quoted value against the cited paper.",
  "Direction-aware baseline: check the rule against Li et al., IEEE Trans. Energy Convers. 32(1), 2017 (Section V.1); fuzzy baseline: replace the generic rule base by a published rule table if available.",
  "Reward-weight sensitivity (Section VI.6, Table XI, in yellow): approve the wording.",
  "Add the last page of Mahtani et al. (IEEE Trans. Ind. Appl. 61(3), 2025) and complete the OpenDER reference.",
  "Update the status of the three earlier papers of the authors in the references.",
  "Add the public code and data link, the corresponding author's e-mail, the funding statement, photographs and full biographies.",
  "Check the IREA author guidelines for the page limit, figure resolution and reference style.",
];
const HEAD = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: runs([{ t: "CHECKLIST (delete before submission)", b: true, hl: true }], 22) }),
  ...CHECK.map((t, i) => new Paragraph({ spacing: { after: 60 }, indent: { left: 340, hanging: 340 }, children: runs([{ t: `${i + 1}. ${t}`, hl: true }], 18) })),
  new Paragraph({ spacing: { after: 400 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ font: FONT, size: 32,
    text: "Is Reinforcement Learning Needed for Virtual Synchronous Generator Tuning? An Oracle-Bounded Comparison of TD3, DDPG and Tuned Adaptive Controllers on an Islanded IEEE 33-Bus Microgrid" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: runs(["Muhammad Binyameen Khan", { t: "1", sup: true }, ", Anant Oonsivilai", { t: "1", sup: true }], 24) }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 850, right: 850 }, spacing: { after: 200 }, children: [
    new TextRun({ text: "Abstract – ", bold: true, font: FONT, size: BODY }),
    new TextRun({ font: FONT, size: BODY, italics: true, text:
      `Deep reinforcement learning is widely reported to outperform fixed and rule-based tuning of virtual synchronous generators (VSGs), and TD3 to outperform DDPG. This paper tests these claims on an islanded IEEE 33-bus feeder with a published 4.9 MVA diesel machine and IEEE 421.5 AC8C exciter, a grid-forming battery VSG with UNIFI reactive-power droop, and PV and wind plants with IEEE 1547-2018 frequency and voltage support, driven by one year of measured load and weather data. TD3 and DDPG learn residual corrections to the virtual inertia and damping and are compared with fixed, bang-bang, RoCoF-adaptive, direction-aware and fuzzy controllers tuned on the same validation data, using five seeds, a hyperparameter screen and 200 held-out test scenarios with Holm-corrected Wilcoxon tests. Neither learner improves the control objective over the fixed VSG it starts from (TD3 ${f2(pct(T.td3.return[0], T.fixed_feasible.return[0]))} %, DDPG ${f2(pct(T.ddpg.return[0], T.fixed_feasible.return[0]))} %, not significant for TD3), and all tuned adaptive rules reduce to the tuned fixed VSG. Oracle bounds explain why: the best per-scenario schedule gains ${f2(omNom.oracle_gain_pct)} % and an event-wise schedule with hindsight ${f2(evNom.event_gain_pct)} %, and no weighting of the objective tested raises the per-scenario bound above ${f2(Math.max(...N.weights.map((r) => r.oracle_gain_pct)))} %. TD3 trains more stably than DDPG (5 of 5 seeds converged against 3 of 5), reduces the maximum frequency deviation by ${f1(nadirRed)} % at the cost of RoCoF and settling time, and, when the load steps are halved after training, recovers about half of the benefit of re-tuning. Against an untuned fixed VSG, the same policies would appear ${f1(gainTd3Untuned)} % better. Benchmarks of learned VSG control should include tuned baselines and oracle bounds.` })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 850, right: 850 }, spacing: { after: 360 }, children: [
    new TextRun({ text: "Keywords: ", bold: true, font: FONT, size: BODY }),
    new TextRun({ italics: true, font: FONT, size: BODY, text: "Deep Reinforcement Learning, IEEE 33-Bus Feeder, Oracle Bound, TD3, Virtual Synchronous Generator" })] }),
];

// ---------- document ----------
const PAGE = { size: { width: 11906, height: 16838 }, margin: { top: 1383, right: 850, bottom: 1701, left: 1417, header: 312, footer: 1134 } };
const sections = [{ properties: { page: PAGE }, children: HEAD }];
let buf = [];
const flush = () => { if (buf.length) { sections.push({ properties: { page: PAGE, type: SectionType.CONTINUOUS, column: { count: 2, space: 567 } }, children: buf }); buf = []; } };
for (const el of C) {
  if (el && el.wide) { flush(); sections.push({ properties: { page: PAGE, type: SectionType.CONTINUOUS }, children: el.wide }); }
  else buf.push(el);
}
flush();
if (figN !== FIG_ORDER.length || tabN !== TAB_ORDER.length) throw new Error(`figures ${figN}/${FIG_ORDER.length}, tables ${tabN}/${TAB_ORDER.length}`);
const doc = new Document({
  creator: "Muhammad Binyameen Khan", title: "IREA manuscript, 33-bus study (PWP template)",
  styles: { default: { document: { run: { font: FONT, size: BODY } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 340, hanging: 227 } } } }] }] },
  sections,
});
Packer.toBuffer(doc).then((b) => {
  const out = path.join(__dirname, "IREA_33bus_manuscript_PWP.docx");
  fs.writeFileSync(out, b);
  console.log("wrote", out, `(${order.length} references, ${figN} figures, ${tabN} tables, ${eqN} equations)`);
  require("child_process").execFileSync("python3", [path.join(__dirname, "insert_equations.py"), out, String(COL_W), String(BODY), "omml_ieee33.json"], { stdio: "inherit" });
});
