// Thesis proposal (SUT format, following the school's proposal template).   Run: node paper/make_proposal.js
// Content is drawn from the author's two earlier studies (TREC / IREMOS manuscripts) and from this repository.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, ShadingType, BorderStyle, PageNumber, Header, LevelFormat, TableOfContents, PageBreak,
  NumberFormat, VerticalAlign,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const PF = (f) => path.join(__dirname, "proposal_figs", f);
const RF = (f) => path.join(ROOT, "results", "figures", f);
const FONT = "Times New Roman";
const SZ = 28;                 // 14 pt body text (template)
const TEXT_W = 8306;           // A4 11906 − 2160 (1.5") − 1440 (1") DXA

// ---------------- helpers ----------------
function runs(parts, size = SZ) {
  return parts.map((p) => {
    if (typeof p === "string") return new TextRun({ text: p, font: FONT, size });
    return new TextRun({ text: p.t, bold: !!p.b, italics: !!p.i, font: FONT, size: p.size || size,
      superScript: !!p.sup, subScript: !!p.sub,
      shading: p.hl ? { type: ShadingType.CLEAR, fill: "FFFF00", color: "auto" } : undefined });
  });
}
const TODO = (t) => ({ t: `[${t}]`, hl: true });
const SUP = (t) => ({ t, sup: true });
const SUB = (t) => ({ t, sub: true });
const I = (t) => ({ t, i: true });
const B = (t) => ({ t, b: true });
// body paragraph: justified, first-line indent, 1.5 spacing
const P = (...parts) => new Paragraph({ children: runs(parts), alignment: AlignmentType.JUSTIFIED,
  indent: { firstLine: 720 }, spacing: { line: 360, after: 120 } });
const PN = (...parts) => new Paragraph({ children: runs(parts), alignment: AlignmentType.JUSTIFIED,
  spacing: { line: 360, after: 120 } });
const CHAP = (n, title) => new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER,
  pageBreakBefore: true, spacing: { before: 240, after: 480, line: 360 },
  children: [new TextRun({ text: `CHAPTER ${n}`, font: FONT, size: 36, bold: true }),
             new TextRun({ text: title, font: FONT, size: 36, bold: true, break: 1 })] });
const UNNUM = (title, toc = true) => new Paragraph({ heading: toc ? HeadingLevel.HEADING_1 : undefined,
  alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { before: 240, after: 360 },
  children: [new TextRun({ text: title, font: FONT, size: 32, bold: true })] });
const H2 = (num, t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120, line: 360 },
  keepNext: true, children: [new TextRun({ text: `${num}\t${t}`, font: FONT, size: SZ, bold: true })],
  tabStops: [{ type: "left", position: 900 }] });
const H3 = (num, t) => new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 180, after: 100, line: 360 },
  keepNext: true, indent: { left: 360 },
  children: [new TextRun({ text: `${num}\t${t}`, font: FONT, size: SZ, bold: true, italics: true })],
  tabStops: [{ type: "left", position: 1300 }] });
const EQ = (txt, n) => new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 80, after: 80, line: 300 },
  indent: { left: 720 }, tabStops: [{ type: "right", position: TEXT_W }],
  children: [new TextRun({ text: txt, font: FONT, size: 26, italics: true }), new TextRun({ text: `\t(${n})`, font: FONT, size: 26 })] });
const NUM = (ref) => (...parts) => new Paragraph({ children: runs(parts), numbering: { reference: ref, level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 60 } });
let numCount = 0;
const numRefs = [];
function newList() { const r = `num${numCount++}`; numRefs.push(r); return NUM(r); }
const BUL = (...parts) => new Paragraph({ children: runs(parts), numbering: { reference: "bul", level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 60 } });

function FIG(file, widthIn, caption) {
  const buf = fs.readFileSync(file);
  const wpx = buf.readUInt32BE(16), hpx = buf.readUInt32BE(20);
  const w = Math.round(widthIn * 96), h = Math.round(w * hpx / wpx);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h },
        altText: { title: caption.slice(0, 40), description: caption, name: path.basename(file) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240, line: 300 }, children: runs([caption], 26) }),
  ];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } };
function TABLE(caption, header, rows, widths, opts = {}) {
  const tot = widths.reduce((a, b) => a + b, 0);
  const fsz = opts.size || 22;
  const cell = (txt, j, isHead, fill) => new TableCell({ borders, width: { size: widths[j], type: WidthType.DXA },
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : (isHead ? { fill: "E8E8E8", type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 40, bottom: 40, left: 80, right: 80 }, verticalAlign: VerticalAlign.CENTER,
    children: String(txt).split("\n").map((line) => new Paragraph({
      alignment: (j === 0 || opts.leftAll) && !isHead ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: [new TextRun({ text: line, font: FONT, size: fsz, bold: isHead })] })) });
  const tRows = [header, ...rows].map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true,
    children: r.map((c, j) => {
      if (c && typeof c === "object" && c.fill !== undefined) return cell(c.t, j, false, c.fill);
      return cell(c, j, i === 0);
    }) }));
  return [
    new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 200, after: 80 }, keepNext: true,
      children: runs([caption], 26) }),
    new Table({ width: { size: tot, type: WidthType.DXA }, columnWidths: widths, rows: tRows }),
    new Paragraph({ spacing: { after: 160 }, children: [] }),
  ];
}
const NOTE = (t) => new Paragraph({ spacing: { after: 160, line: 276 }, children: runs([{ t, i: true, size: 22 }]) });

const C = [];       // body (chapters)
// =====================================================================================
// FRONT MATTER
// =====================================================================================
const TITLE = "TOWARD FEASIBLE SYNTHETIC INERTIA: REINFORCEMENT-LEARNING-DRIVEN VIRTUAL SYNCHRONOUS GENERATOR CONTROL FOR LOW-INERTIA PV–WIND–BESS MICROGRIDS";
const cover = [
  new Paragraph({ spacing: { before: 600 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: 360 }, children: [new TextRun({ text: TITLE, font: FONT, size: 36, bold: true })] }),
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "MUHAMMAD BINYAMEEN KHAN", font: FONT, size: 32, bold: true })] }),
  new Paragraph({ spacing: { before: 3600 }, children: [] }),
  ...["A Proposal Submitted in Partial Fulfillment of the", "Requirements for the Degree of Master of Engineering in",
      "School of Electrical Engineering", "Institute of Engineering", "Suranaree University of Technology"].map((t) =>
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: 360 }, children: [new TextRun({ text: t, font: FONT, size: SZ, bold: true })] })),
];

const infoRow = (k, v) => new TableRow({ children: [
  new TableCell({ borders: noBorders, width: { size: 2300, type: WidthType.DXA },
    children: [new Paragraph({ children: runs([k]) })] }),
  new TableCell({ borders: noBorders, width: { size: 6006, type: WidthType.DXA },
    children: [new Paragraph({ alignment: AlignmentType.LEFT, children: runs(Array.isArray(v) ? v : [v]) })] })] });
const front = [
  new Table({ width: { size: 8306, type: WidthType.DXA }, columnWidths: [2300, 6006], rows: [
    infoRow("Thesis Title", "Toward feasible synthetic inertia: reinforcement-learning-driven virtual synchronous generator control for low-inertia PV–wind–BESS microgrids"),
    infoRow("Author", "Mr. Muhammad Binyameen Khan"),
    infoRow("Degree", ["Master of Engineering in Electrical Engineering ", TODO("confirm degree title")]),
    infoRow("Advisor", "Assoc. Prof. Dr. Anant Oonsivilai")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 480, after: 240 },
    children: [new TextRun({ text: "ABSTRACT", font: FONT, size: 32, bold: true })] }),
  PN("Converter-interfaced PV and wind generation remove the rotating mass that once stabilised frequency, so the frequency of a small microgrid now depends on how its battery energy storage system (BESS) converter is controlled. A virtual synchronous generator (VSG) lets that converter emulate inertia and damping, and deep reinforcement learning (DRL) has been proposed to adapt both parameters online. This thesis argues that such adaptation is useful only if the emulated inertia and damping are physically deliverable and only if its benefit is measured against properly tuned alternatives. It proposes a converter-headroom feasibility constraint, derived from grid-code limits on the rate of change of frequency and on the frequency deviation, and trains DDPG and TD3 agents to schedule the VSG parameters under it in a fully converter-interfaced microgrid driven by measured 1-Hz weather and in a hybrid diesel–PV–wind–BESS microgrid driven by one year of ERA5 and NASA POWER data for Nakhon Ratchasima, Thailand. The controllers are compared with tuned constant and rule-based VSGs over several seeds, an oracle bounds the achievable gain before training, and the results are validated in MATLAB and in a three-phase electromagnetic-transient model. Preliminary results show that literature-style high-gain VSG settings need far more headroom than the converter can reserve, that learned controllers match a tuned VSG with 19–21 % less reserved headroom in the converter-only system, that adaptation can gain at most 2.1 % in the hybrid system, and that the constraint reduces undeliverable commitments of a learned policy from 5.07 s to 0.02 s per 30 s episode."),
];

// =====================================================================================
// CHAPTER 1  INTRODUCTION
// =====================================================================================
C.push(CHAP(1, "INTRODUCTION"));
C.push(H2("1.1", "General Introduction"));
C.push(P("Power systems are moving away from large synchronous generators towards photovoltaic (PV) and wind plants connected through power-electronic converters. A synchronous machine stores kinetic energy in its rotor and releases it automatically when the frequency falls; a converter-interfaced source does not, because the converter decouples whatever rotates behind it from the grid (Milano et al., 2018; Ulbig et al., 2014). As converter-interfaced generation grows, the inertia of the system falls, the rate of change of frequency (RoCoF) after a disturbance rises, and the frequency nadir becomes deeper. The effect is strongest in small and isolated microgrids, where a single load step of a few hundred kilowatts is a large fraction of the total demand."));
C.push(P("A battery energy storage system (BESS) whose converter is controlled as a virtual synchronous generator (VSG) can restore part of the missing behaviour. The VSG reproduces the swing equation of a synchronous machine in software, with a virtual inertia J and a virtual damping D that the designer can choose (Zhong and Weiss, 2011; Bevrani et al., 2014). Because J and D are only numbers in a controller, they can also be changed while the system runs, by rules or by learning, and deep reinforcement learning (DRL) has become a popular way to do so. This thesis studies when such adaptive, learned VSG control is physically feasible and when it is actually worth having."));

C.push(H2("1.2", "Problem Statement"));
C.push(P("Thailand, like many countries, is adding solar and wind capacity to reduce fuel imports and emissions, and remote communities, islands and industrial sites increasingly operate as hybrid microgrids in which a diesel generator, PV, wind and a BESS share the load. In such systems the frequency is set by very little rotating mass. A virtual synchronous generator on the BESS converter is the natural remedy, but three practical problems limit how it is designed today."));
C.push(P("First, virtual inertia and damping are not free. Every second of virtual inertia and every unit of damping commits the converter to inject power in proportion to the RoCoF and to the frequency deviation. A battery that is already discharging to cover the evening peak, or one whose state of charge (SoC) is close to its limit, may not be able to deliver that power. Most adaptive VSG schemes in the literature, rule-based or learned, bound J and D only by fixed ranges and never check them against the power the converter has left (Alipoor et al., 2015; Li et al., 2017; Oboreh-Snapps et al., 2024). A controller that promises inertia it cannot deliver gives a false sense of security and saturates the converter exactly when it is needed."));
C.push(P("Second, the benefit of learning is often overstated. DRL results vary strongly between training runs and depend on which checkpoint is kept (Henderson et al., 2018; Agarwal et al., 2021), yet learned VSG controllers are frequently compared with hand-picked fixed gains from a single training run. Whether a learned controller really improves on a properly tuned conventional VSG, and by how much it could improve at most, usually remains unanswered."));
C.push(P("Third, most learning studies rely on averaged (RMS) frequency models. It is not obvious that the conclusions survive in a three-phase circuit with a phase-locked loop (PLL) and a converter that limits its output on measured current and power."));
C.push(P("This thesis therefore addresses adaptive VSG control as a feasibility problem first and a learning problem second. It develops a converter-headroom constraint that keeps virtual inertia and damping within what the BESS and a de-loaded PV plant can deliver, trains DDPG and TD3 agents to schedule the VSG parameters under that constraint, evaluates them fairly against tuned alternatives, bounds the achievable benefit, and validates the results beyond the averaged model."));

C.push(H2("1.3", "Research Objectives"));
C.push(P("The main objectives of this thesis are as follows,"));
{ const L = newList();
  C.push(L("To formulate a converter-headroom feasibility constraint that limits the virtual inertia and damping of a VSG to the power that the BESS, and a de-loaded PV plant, can deliver at the grid-code limits on RoCoF and frequency deviation, and to compare alternative forms of this constraint."));
  C.push(L("To develop DDPG- and TD3-based adaptive VSG controllers that schedule the virtual inertia and damping in real time under this constraint, for a fully converter-interfaced microgrid and for a hybrid diesel–PV–wind–BESS microgrid driven by real weather data."));
  C.push(L("To evaluate the learned controllers fairly, against constant and rule-based VSGs tuned on the same data and objective, over several training seeds with statistical tests, and to bound in advance the gain that any adaptive scheduler can achieve."));
  C.push(L("To validate the models and controllers beyond the averaged model by an independent MATLAB implementation and a three-phase electromagnetic-transient (EMT) model in MATLAB/Simscape Electrical.")); }

C.push(H2("1.4", "Scope and Limitations"));
C.push(P("The thesis is carried out in simulation within the following scope:"));
{ const L = newList();
  C.push(L("Two 50 Hz test systems are studied. Study 1 is a fully converter-interfaced microgrid with a 500 kW PV plant, a 500 kW Type-4 wind turbine, a 2500 kVA grid-forming BESS and an 1800 kW load. Study 2 is a hybrid microgrid on a 2 MVA base with a 0.5 MW diesel generator, a 1.0 MW wind turbine, a 0.8 MW de-loaded PV plant and a 0.5 MW / 2 MWh BESS operated as a VSG."));
  C.push(L("Weather inputs are measured 1-Hz irradiance and wind records (Study 1) and one year (2024) of hourly ERA5 wind and NASA POWER solar data for Nakhon Ratchasima, Thailand (Study 2), split into training, validation and test periods."));
  C.push(L("Disturbances are load contingencies of both signs, two or three per 30 s episode, superimposed on the weather-driven operating point."));
  C.push(L("The VSG parameters scheduled by the controllers are the virtual inertia J and damping D, together with the reactive droop gain (Study 1) or the PV share of the fast support (Study 2)."));
  C.push(L("The learning algorithms are DDPG and TD3, implemented in Python with PyTorch. The benchmarks are no virtual inertia, BESS droop, literature-style fixed VSGs, a validation-tuned fixed VSG and rule-based adaptive VSGs."));
  C.push(L("The network is represented as a single bus. Multi-bus power flow, protection coordination, converter switching and hardware-in-the-loop experiments are outside the scope; the EMT model uses an average converter model and a classical diesel machine model.")); }

C.push(H2("1.5", "Conception"));
C.push(P("The main idea of the thesis is that synthetic inertia must be feasible before it can be optimal. Fig. 1.1 shows the conceptual framework. Weather data, load events and grid-code limits drive two microgrid models. A DRL agent proposes the VSG parameters, but every proposal passes a rate limiter and then a headroom feasibility layer before it reaches the converter, so that the converter is never asked for more than it can deliver. The resulting controllers are evaluated against tuned conventional VSGs over several seeds, compared with an oracle that bounds the best achievable adaptation, and validated in MATLAB and in a three-phase EMT model."));
C.push(...FIG(PF("fig_concept.png"), 6.0, "Fig. 1.1 Conceptual framework of the thesis"));

C.push(H2("1.6", "Research Benefits"));
C.push(P("The thesis is expected to provide the following benefits:"));
{ const L = newList();
  C.push(L("A simple, deployable feasibility check that any adaptive VSG controller, learned or rule-based, can use to avoid committing inertia and damping that the converter cannot deliver."));
  C.push(L("Evidence, under a fair and statistically sound protocol, of when DRL-based VSG scheduling improves on a well-tuned conventional VSG and when it does not, together with a cheap pre-training test (the oracle bound) that tells a designer whether training an agent is worthwhile."));
  C.push(L("A reusable modelling and data pipeline for Thai microgrids based on freely available ERA5 and NASA POWER data, with open code in Python and MATLAB."));
  C.push(L("Validated models, from the averaged model to a three-phase EMT model, that show which conclusions of averaged-model studies hold at circuit level and which, such as PLL-measured RoCoF, do not.")); }

// =====================================================================================
// CHAPTER 2  LITERATURE REVIEW
// =====================================================================================
C.push(CHAP(2, "LITERATURE REVIEW"));
C.push(H2("2.1", "Introduction"));
C.push(P("Research on virtual synchronous generators has moved from emulating a synchronous machine with fixed parameters, through rule-based adaptation of the virtual inertia and damping, to learning-based adaptation with deep reinforcement learning. In parallel, work on grid-forming converters has shown that the converter rating limits what any of these controllers can deliver. This chapter first describes how the literature was searched and selected, following the PRISMA 2020 guideline (Page et al., 2021), then summarises the selected studies in two tables, discusses them by theme, and closes with the research gaps that this thesis addresses."));

C.push(H2("2.2", "Systematic Search and Selection (PRISMA)"));
C.push(P("The search covers peer-reviewed literature published from 2015 to 2026 in four databases: Scopus, IEEE Xplore, ScienceDirect and Web of Science. The search strings combine two concept blocks, the VSG or virtual-inertia block and the adaptation or learning block, and are adapted to the syntax of each database as listed in Table 2.1. Reference lists of the included studies were also screened (citation searching)."));
C.push(...TABLE("Table 2.1 Databases and search strings (searched on " + "____" + ")",
  ["Database", "Search string (title, abstract and keywords)"],
  [["Scopus", "TITLE-ABS-KEY ( ( \"virtual synchronous generator\" OR \"virtual synchronous machine\" OR \"virtual inertia\" OR \"synthetic inertia\" ) AND ( adaptive OR \"reinforcement learning\" OR DDPG OR TD3 OR \"actor-critic\" ) ) AND PUBYEAR > 2014 AND PUBYEAR < 2027 AND ( DOCTYPE ( ar ) OR DOCTYPE ( cp ) ) AND LANGUAGE ( english )"],
   ["IEEE Xplore", "(\"virtual synchronous generator\" OR \"virtual synchronous machine\" OR \"virtual inertia\" OR \"synthetic inertia\") AND (adaptive OR \"reinforcement learning\" OR DDPG OR TD3 OR \"actor-critic\"); All Metadata; 2015–2026; journals and conferences"],
   ["ScienceDirect", "Title, abstract, keywords: (\"virtual synchronous generator\" OR \"virtual inertia\") AND (\"reinforcement learning\" OR adaptive); 2015–2026; research articles"],
   ["Web of Science", "TS=((\"virtual synchronous generator\" OR \"virtual synchronous machine\" OR \"virtual inertia\" OR \"synthetic inertia\") AND (adaptive OR \"reinforcement learning\" OR DDPG OR TD3 OR \"actor-critic\")); 2015–2026; articles and proceedings papers"]],
  [1700, 6606], { leftAll: true }));
C.push(P("Records were screened on title and abstract and then on full text against the following criteria. A study was included if (I1) it is a peer-reviewed journal or conference paper in English published in 2015–2026; (I2) it concerns VSG or virtual-inertia control of converter-interfaced storage or generation; (I3) it adapts the inertia and/or damping online, by rules or by learning, or it addresses the converter capability that limits such control; and (I4) it reports quantitative frequency-dynamic results. Studies were excluded if the VSG parameters were fixed (E1), no quantitative frequency results were reported (E2), the work was not peer reviewed (E3), or it duplicated an already included study of the same model (E4). Foundational works on the VSG concept and on DRL evaluation practice were retained as background."));
C.push(P("Fig. 2.1 shows the selection flow. Seventeen studies were included in the qualitative synthesis and are summarised in Tables 2.2 and 2.3. ", TODO("AUTHOR: run the four searches in Table 2.1 through the SUT library, record the date and the number of hits per database, and fill every n = ____ in Fig. 2.1 and in this paragraph; keep the search log as an appendix")));
C.push(...FIG(PF("fig_prisma.png"), 5.4, "Fig. 2.1 PRISMA 2020 flow diagram of the literature selection"));

C.push(H2("2.3", "Literature Overview"));
C.push(P("The included studies fall into two groups. Table 2.2 lists the studies on the VSG concept, rule-based adaptive inertia and damping, and converter current limiting. Table 2.3 lists the learning-based VSG and virtual-inertia studies, including the two earlier studies of this thesis."));
C.push(...TABLE("Table 2.2 VSG, rule-based adaptive inertia and converter-capability studies",
  ["Reference", "Topic", "Objective", "Method", "Description"],
  [["Zhong and Weiss (2011)", "Synchronverters: inverters that mimic synchronous generators", "-make an inverter behave as a synchronous generator", "-synchronous-machine equations in the converter controller", "-foundational VSG concept\n-fixed inertia and damping"],
   ["Bevrani et al. (2014)", "Virtual synchronous generators: a survey and new perspectives", "-review VSG concepts and topologies", "-survey", "-classifies VSG implementations and open issues"],
   ["Alipoor et al. (2015)", "Power system stabilization using VSG with alternating moment of inertia", "-damp oscillations after a disturbance", "-bang-bang rule switching J with the rotor acceleration", "-adapts inertia only\n-no converter capability check"],
   ["Li et al. (2017)", "Self-adaptive inertia and damping combination control of VSG", "-support frequency stability", "-rule adapting J and D together", "-adaptive J and D\n-thresholds tuned for designed events"],
   ["Han et al. (2023)", "Adaptive VSG control considering energy storage SOC constraints", "-adapt VSG parameters within battery limits", "-rule with SoC-dependent limits", "-considers SoC limits only, not the full converter headroom"],
   ["Shi et al. (2024)", "Adaptive optimal control of VSG inertia and damping parameters", "-improve dynamic response", "-coordination through the power–angle characteristic", "-adaptive J and D\n-no learning"],
   ["Paquette and Divan (2015)", "Virtual impedance current limiting for inverters in microgrids with synchronous generators", "-limit inverter current", "-virtual impedance", "-shows that the converter rating bounds grid-forming support"],
   ["Qoria et al. (2020)", "Current limiting algorithms and transient stability of grid-forming VSCs", "-compare current limiting methods", "-analysis and simulation", "-current limits change transient stability of grid-forming control"]],
  [1500, 1900, 1700, 1600, 1606]));
C.push(...TABLE("Table 2.3 Learning-based VSG and virtual-inertia studies",
  ["Reference", "Topic", "Objective", "Method", "Description"],
  [["Afifi et al. (2023)", "DDPG-controlled VSG for an islanded microgrid", "-improve frequency regulation", "-DDPG", "-co-regulates droop, J and D\n-no headroom check"],
   ["Lu and Zhuan (2024)", "Adaptive control of VSG parameters based on soft actor–critic", "-improve transient response", "-SAC", "-tunes J and D\n-settling-time term in the reward"],
   ["Egbomwan et al. (2023)", "TD3-based virtual inertia control for inverter-interfaced DGs", "-frequency regulation in microgrids", "-TD3", "-learned virtual inertia control"],
   ["Oboreh-Snapps et al. (2024)", "VSG control using the TD3 method", "-adaptive VSG tuning", "-TD3", "-J and D tuning\n-real-time digital simulator validation"],
   ["Egbomwan et al. (2025)", "Learning-based predictive virtual inertia control", "-frequency regulation in low-inertia grids", "-learning combined with prediction", "-predictive virtual inertia control"],
   ["Criollo et al. (2026)", "Virtual inertia control in microgrid clusters with DRL", "-frequency response of microgrid clusters", "-DDPG, TD3, SAC", "-compares several DRL algorithms"],
   ["Li et al. (2026)", "Adaptive VSG control based on RL strategy optimization", "-adaptive VSG parameters", "-TD3", "-benchmarked against fixed, rule-based, DDPG and RBF controllers"],
   ["Khan et al. (TREC, under review)", "RL-based VSG control for a low-inertia solar–wind–BESS microgrid: a headroom-feasible approach", "-reduce IAE and reserved headroom", "-DDPG and TD3 schedule J, D, Kq", "-introduces headroom requirement and proportional derating\n-single seed, untuned baselines"],
   ["Khan et al. (IREMOS, submitted)", "Headroom-feasible adaptive VSG control with DRL: multi-seed comparison with tuned controllers", "-fair comparison with tuned baselines", "-DDPG and TD3, ten seeds", "-measured 1-Hz weather\n-learning trades regulation for headroom"]],
  [1500, 1900, 1700, 1600, 1606]));

C.push(H2("2.4", "VSG and Adaptive Inertia Control"));
C.push(P("The synchronverter of Zhong and Weiss (2011) showed that a converter can reproduce the equations of a synchronous machine inside its controller, so that it responds to frequency changes with an inertial and a damping power. Bevrani et al. (2014) reviewed the many VSG variants that followed. In these designs the virtual inertia and damping are constants, normally sized for the worst expected event. Large constants occupy converter capacity during long quiet periods, while small constants may fail to arrest a severe event, and this motivated adaptive schemes. Alipoor et al. (2015) switch the inertia between two values depending on whether the virtual rotor is accelerating or decelerating. Li et al. (2017) adapt inertia and damping together, Shi et al. (2024) coordinate them through the power–angle characteristic, and Han et al. (2023) add limits based on the battery state of charge. Rule-based schemes are transparent and cheap to implement, but their thresholds are tuned for the disturbances considered in design, and none of them checks the commanded inertia and damping against the power that the converter has left."));

C.push(H2("2.5", "Learning-Based VSG and Virtual Inertia Control"));
C.push(P("Deep reinforcement learning is attractive for VSG tuning because the mapping from the system state to good parameters is nonlinear and the actions are continuous (Glavic, 2019). DDPG (Lillicrap et al., 2016) and TD3 (Fujimoto et al., 2018), which corrects the value overestimation of DDPG, are the usual choices. Afifi et al. (2023) use DDPG to regulate droop, inertia and damping in an islanded microgrid; Lu and Zhuan (2024) tune inertia and damping with soft actor–critic and a settling-time reward; Egbomwan et al. (2023, 2025) apply TD3 and a learning-based predictive scheme to virtual inertia control; and Oboreh-Snapps et al. (2024) validate a TD3-based VSG on a real-time digital simulator. Criollo et al. (2026) compare DDPG, TD3 and soft actor–critic for microgrid clusters, and Li et al. (2026) benchmark a TD3-based adaptive VSG against fixed, rule-based, DDPG and RBF controllers. Comparisons between DDPG and TD3 therefore already exist; what is still missing is a check of the learned parameters against converter capability and an evaluation protocol that makes the reported gains trustworthy."));
C.push(P("The two earlier studies of this thesis addressed the first part of that gap for a fully converter-interfaced microgrid. Khan et al. (TREC, under review) introduced a headroom requirement derived from the grid-code limits and derated the VSG parameters proportionally when the requirement exceeded the available headroom. Khan et al. (IREMOS, submitted) repeated the comparison over ten seeds with tuned constant and rule-based baselines and measured weather, and found that the learned controllers match the regulation of the tuned constant VSG with about one fifth less reserved headroom, rather than dominating it."));

C.push(H2("2.6", "Converter Capability and Evaluation Practice"));
C.push(P("Studies of grid-forming converters show that current limiting changes what the controller can deliver and even its transient stability (Paquette and Divan, 2015; Qoria et al., 2020). Yet adaptive VSG formulations rarely translate the converter rating into limits on the virtual inertia and damping. On the evaluation side, Henderson et al. (2018) and Agarwal et al. (2021) show that DRL results depend strongly on the random seed and on checkpoint selection, so that a single run, or a comparison against untuned baselines, can overstate the benefit of learning. Finally, most learning studies use averaged frequency models, and only a few, such as Oboreh-Snapps et al. (2024), test a learned VSG in a more detailed simulator."));

C.push(H2("2.7", "Research Gaps"));
C.push(P("Table 2.4 compares the reviewed studies on the aspects that matter for feasible synthetic inertia. Five gaps stand out: (i) the commanded inertia and damping are almost never checked against converter headroom; (ii) learned controllers are rarely compared with tuned baselines over several seeds; (iii) no study bounds in advance how much adaptation can gain; (iv) systems in which a synchronous machine shares the transient with the VSG are rarely considered together with learning; and (v) learned VSG schedules are seldom validated at circuit level. The proposed framework addresses all five."));
const Y = "✓", N = "–";
C.push(...TABLE("Table 2.4 Comparison of previous research and the proposed framework",
  ["Reference", "Method", "Adapted parameters", "Headroom constraint on J, D", "Tuned baselines, multi-seed statistics", "Circuit-level / real-time validation"],
  [["Alipoor et al. (2015)", "Bang-bang rule", "J", N, N, N],
   ["Li et al. (2017)", "Adaptive rule", "J, D", N, N, N],
   ["Han et al. (2023)", "Rule with SoC limits", "J, D", "SoC limits only", N, N],
   ["Shi et al. (2024)", "Adaptive optimal rule", "J, D", N, N, N],
   ["Afifi et al. (2023)", "DDPG", "droop, J, D", N, N, N],
   ["Lu and Zhuan (2024)", "SAC", "J, D", N, N, N],
   ["Egbomwan et al. (2023)", "TD3", "virtual inertia", N, N, N],
   ["Oboreh-Snapps et al. (2024)", "TD3", "J, D", N, N, Y + " (RTDS)"],
   ["Criollo et al. (2026)", "DDPG, TD3, SAC", "J, D", N, N, N],
   ["Li et al. (2026)", "TD3 vs DDPG, rule, RBF", "J, D", N, "baselines only", N],
   ["Khan et al. (TREC)", "DDPG vs TD3", "J, D, Kq", Y + " (sum rule)", N, N],
   ["Khan et al. (IREMOS)", "DDPG vs TD3", "J, D, Kq", Y + " (sum rule)", Y + " (10 seeds)", N],
   [{ t: "Proposed framework", fill: "E2EFDA" }, { t: "Residual DDPG / TD3 + oracle bound", fill: "E2EFDA" },
    { t: "J, D, Kq or PV share α", fill: "E2EFDA" }, { t: Y + " direction-aware; rules compared", fill: "E2EFDA" },
    { t: Y + " (5–10 seeds, Holm)", fill: "E2EFDA" }, { t: Y + " MATLAB + EMT", fill: "E2EFDA" }]],
  [1650, 1450, 1250, 1350, 1300, 1306], { size: 21 }));
NOTE("–: not reported in the cited formulation (as summarised in Khan et al., IREMOS). RTDS: real-time digital simulator.");

// =====================================================================================
// CHAPTER 3  METHODOLOGY
// =====================================================================================
C.push(CHAP(3, "METHODOLOGY"));
C.push(H2("3.1", "Introduction"));
C.push(P("This chapter presents the models, the feasibility constraint, the learning formulation and the evaluation and validation methods. The thesis is organised as two connected studies (Fig. 1.1). Study 1 develops and tests the headroom-feasible learning framework in a fully converter-interfaced microgrid. Study 2 transfers it to a hybrid microgrid that contains a synchronous diesel generator, adds real site data for Thailand, refines the feasibility constraint, bounds the benefit of adaptation and validates the results at circuit level. Common elements are described once; differences between the studies are stated where they occur."));

C.push(H2("3.2", "Weather Data and Operating Points"));
C.push(P("Study 1 uses measured high-resolution records at their recorded levels: 1-Hz global horizontal irradiance (GHI) from the Cabauw Baseline Surface Radiation Network station in the Netherlands on 31 March, 17 July and 22 July 2015 (259,065 samples; Mol et al., 2023), and 80 m sonic-anemometer wind speed from the FINO1 offshore platform, 21–23 January 2007, averaged to 1-s means (255,599 samples; Cheynet, 2025). The records are split chronologically into training (70 %), validation (15 %) and test (15 %) segments, and each 30 s episode is a window cut from them according to the scenario (clear day, cloud shadow, wind gust drop, night, combined stress)."));
C.push(P("Study 2 uses one year (2024) of hourly data for the site of the thesis, Nakhon Ratchasima, Thailand (14.98° N, 102.10° E, 226 m). The 100 m wind components come from the ERA5 reanalysis (Hersbach et al., 2020) on a 2 × 2 grid around the site and are interpolated bilinearly; irradiance and temperature come from NASA POWER, converted from local solar time to UTC. Air density is computed from the temperature and the pressure at the site elevation. Because only one year is available, the hours are divided into weekly blocks, five for training, one for validation and one for testing in every seven weeks, so that all seasons appear in every subset. Within each hour, wind turbulence (intensity 10 %) and load noise (0.5 %) are added, and two or three load steps of 0.2–0.4 MW are applied in each 30 s episode."));

C.push(H2("3.3", "Photovoltaic Model"));
C.push(P("Because the frequency dynamics are much slower than the electrical response of the panels, the PV plant is represented by an algebraic irradiance–temperature model (Skoplaki and Palyvos, 2009):"));
C.push(EQ("T_cell = T_amb + k_NOCT · G", "3.1"));
C.push(EQ("P_pv = η_deg · P_pv,rated · (G / G_ref) · [1 − C_T (T_cell − T_ref)],     0 ≤ P_pv ≤ P_pv,rated", "3.2"));
C.push(P("with G_ref = 1000 W/m², C_T = 0.0045 °C⁻¹, T_ref = 25 °C, k_NOCT = 0.030 °C·m²/W and η_deg = 0.995 in Study 1. In Study 2 the plant is operated 15 % below its maximum power point (de-loaded MPPT), so that it delivers P_pv,0 = (1 − d)·P_MPP and holds a reserve d·P_MPP that can be released within 80 ms as fast frequency support."));

C.push(H2("3.4", "Wind Turbine Model"));
C.push(P("In Study 1 the Type-4 PMSG turbine extracts the mechanical power (Slootweg et al., 2003)"));
C.push(EQ("P_m = ½ ρ π R² C_p(λ, β) v_w³", "3.3"));
C.push(EQ("C_p = 0.5176 (116/λ_i − 0.4β − 5) e^(−21/λ_i) + 0.0068 λ,     1/λ_i = 1/(λ + 0.08β) − 0.035/(β³ + 1)", "3.4"));
C.push(P("with ρ = 1.225 kg/m³ and R = 18.9 m, which gives 500 kW at the rated speed of 11.5 m/s, an optimal tip-speed ratio of 8.10 and cut-in and cut-out speeds of 3 and 25 m/s. In Study 2, where the wind is hourly, a pitch-regulated IEC class III power curve with density correction is used (IEC 61400-12-1),"));
C.push(EQ("P_w = P_r (v'³ − v_ci³) / (v_r³ − v_ci³) for v_ci ≤ v' < v_r,   P_w = P_r for v_r ≤ v' < v_co,   v' = v (ρ/1.225)^(1/3)", "3.5"));
C.push(P("with P_r = 1.0 MW, v_ci = 2.5 m/s, v_r = 10 m/s, v_co = 25 m/s and a 100 m hub, chosen because the site is a low-wind site (mean 4.2 m/s at 100 m)."));

C.push(H2("3.5", "BESS and VSG Dynamics"));
C.push(H3("3.5.1", "Study 1: fully converter-interfaced microgrid"));
C.push(P("All quantities are in per unit on S_base = 2500 kVA, with Δω = (f − f_0)/f_0 and f_0 = 50 Hz. The VSG injects a component proportional to the rate of change and to the deviation of frequency, the damping term acting on the PLL-measured deviation Δω_m:"));
C.push(EQ("p_vsg = −2 J_eff dΔω/dt − D_eff Δω_m", "3.6"));
C.push(P("Substituting (3.6) into the swing equation of the system, which retains a residual inertia H_sys = 0.5 s from converter control and load, gives the closed form used in simulation (Kundur, 1994):"));
C.push(EQ("2 (H_sys + J_eff) dΔω/dt = ΔP_ext − D_eff Δω_m", "3.7"));
C.push(EQ("ΔP_ext = (P_pv + P_w + P_sch − P_load)/S_base + p_dr,     T_dr dp_dr/dt = −(1/R) Δω_m − p_dr", "3.8"));
C.push(P("where p_dr is the primary droop of the BESS (1/R = 10 pu, T_dr = 0.5 s). The scheduled BESS set-point follows a filtered estimate of the renewable generation, so that only the fast residual reaches the network:"));
C.push(EQ("τ_sch dP_gen,f/dt = P_pv + P_w − P_gen,f,     P_sch = P_load,nom (V/V_nom)^kp − P_gen,f", "3.9"));
C.push(P("with τ_sch = 1 s. Reactive support is a voltage droop bounded by the apparent-power circle, so frequency and voltage support compete for the same rating, and the frequency is observed through a PLL with a first-order lag and measurement noise:"));
C.push(EQ("q_vsg = K_q (V_nom − V),     |q_vsg| ≤ √(S_rated² − P_bess²) / S_base", "3.10"));
C.push(EQ("τ_pll df_m/dt = f + n − f_m,     n ~ N(0, σ_pll²),  τ_pll = 20 ms, σ_pll = 8 mHz", "3.11"));
C.push(H3("3.5.2", "Study 2: hybrid diesel–VSG microgrid"));
C.push(P("The diesel synchronous generator (SG) and the VSG are voltage sources behind reactances meeting at the load bus. Linearised around the operating point on a 2 MVA base, the network shares a net imbalance ΔP_net between the two machines in proportion to their synchronising coefficients K_d and K_s, and the bus frequency is their coefficient-weighted mean speed:"));
C.push(EQ("P_v = K_s (K_d δ + ΔP_net) / (K_d + K_s),     ΔP_net = ΔP_L − ΔP_w + D_L P_L0 Δω_b", "3.12"));
C.push(EQ("Δω_b = (K_d Δω_d + K_s Δω_v) / (K_d + K_s)", "3.13"));
C.push(EQ("2 H_d dΔω_d/dt = ΔP_m − ΔP_e,d − D_d (Δω_d − Δω_b)", "3.14"));
C.push(EQ("2 J_v dΔω_v/dt = P_set − P_v − D_v Δω_v,     dδ/dt = ω_0 (Δω_v − Δω_d)", "3.15"));
C.push(P("Here δ is the angle of the virtual rotor relative to the SG rotor, ΔP_m follows a droop governor (5 %) with governor and engine lags (0.2 s, 0.5 s) and automatic generation control, and P_set is moved by an integral BESS secondary control. With K_d = 0.8 pu and K_s = 2.0 pu the VSG takes about 71 % of every load step at the instant it occurs, whatever J_v and D_v are. The VSG power is limited to the band the BESS and PV can deliver,"));
C.push(EQ("−(P_ch,max(SoC) + P_b0) + P_pv,s ≤ P_v ≤ P_dis,max(SoC) − P_b0 + P_pv,s", "3.16"));
C.push(P("where P_b0 is the BESS power dispatched by a rule-based energy management system (EMS) that keeps the diesel near 60 % of its rating, the SoC-dependent limits taper linearly near the SoC bounds (0.10–0.95), and P_pv,s = α P_v is the PV share of the support. The model is integrated at 2 ms and frequency is measured through a 20 ms filter."));

C.push(H2("3.6", "Converter Headroom Feasibility"));
C.push(P("Sustaining (3.6) or (3.15) requires active-power headroom that the converter may not possess. Study 1 uses the worst case admitted by the grid code, in which the frequency reaches the RoCoF limit and the deviation limit at the same time:"));
C.push(EQ("h_req = 2J · RoCoF_max/f_0 + D · Δf_max/f_0 = 0.08 J + 0.01 D   (RoCoF_max = 2 Hz/s, Δf_max = 0.5 Hz)", "3.17"));
C.push(EQ("h_avail = (S_rated − |P_sch + p_dr S_base|) / S_base", "3.18"));
C.push(EQ("(J_eff, D_eff) = (J, D) · min(1, h_avail / h_req)", "3.19"));
C.push(P("One second of virtual inertia therefore commits as much headroom as 8 pu of damping. The parameters are also slew-limited to a full traverse in T_slew = 0.30 s, and (3.19) is applied identically to every controller. Study 2 refines the constraint in three ways. First, the headroom is direction-aware: upward headroom applies while the frequency is at or below nominal and downward headroom during an over-frequency event,"));
C.push(EQ("h_up = max(P_dis,max(SoC) − P_b0, 0) + d·P_MPP,     h_dn = max(P_ch,max(SoC) + P_b0, 0) + P_pv,0", "3.20"));
C.push(P("Second, because the RoCoF peaks immediately after a step, when the deviation is still near zero, and the deviation peaks at the nadir, when the RoCoF is zero, each mechanism is sized at its own peak (time-separated requirement), with Δf_band = 0.2 Hz and RoCoF_lim = 1 Hz/s:"));
C.push(EQ("h_req,max = max(2 J_v · RoCoF_lim, D_v · Δf_band) ≤ h", "3.21"));
C.push(P("Third, two derating methods are compared: clipping each parameter to its own bound (J_v ≤ h/(2 RoCoF_lim), D_v ≤ h/Δf_band), and scaling both by one factor as in (3.19). In all cases the commanded parameters pass a 0.25 s rate limiter before the feasibility step, so that feasibility takes priority over smoothness. The time during which the applied pair violates the requirement (infeasible commitment) measures what the constraint prevents."));

C.push(H2("3.7", "Reinforcement Learning Formulation"));
C.push(P("Adaptive tuning is formulated as a Markov decision process (Sutton and Barto, 2018). In Study 1 the observation contains the measured frequency deviation and RoCoF, the PV and wind power, wind speed, irradiance, SoC, voltage deviation, BESS power, the parameters in force (J, D, K_q) and the available headroom; the action is a_t = (J, D, K_q) with J ∈ [0.05, 15] s, D ∈ [5, 60] pu and K_q ∈ [2, 20] pu, decided every 20 ms. The reward, evaluated on the true frequency, penalises the frequency deviation, the RoCoF over a 500 ms relay window (with a hinge above 2 Hz/s), voltage error, action changes, SoC excursions, the reserved headroom h_req and the infeasible part max(0, h_req − h_avail), and rewards survival within the operating band; a protection trip ends the episode with a penalty."));
C.push(P("In Study 2 the observation has 16 normalised entries (frequency deviation and RoCoF, VSG power, virtual-rotor slip, upward, downward and PV headroom, SoC, wind, PV and diesel power, diesel spare capacity, load, and the applied J_v, D_v and α), and the decision interval is 50 ms. The action is residual (Silver et al., 2018): a = 0 reproduces a validation-tuned VSG (J_0, D_0, α_0), and each component moves the parameter towards its projected bound,"));
C.push(EQ("J_v = J_0 + a_1 (J_ub − J_0) for a_1 ≥ 0,     J_v = J_0 + a_1 (J_0 − J_min) for a_1 < 0   (similarly for D_v and α)", "3.22"));
C.push(P("The interval cost penalises the frequency outside the ±0.2 Hz band, the RoCoF above 1 Hz/s, the fast VSG power above its set-point, the BESS power, converter saturation and limit violations:"));
C.push(EQ("c = w_f⟨(|Δf|−0.2)₊²⟩/0.5² + w_in⟨Δf²⟩/0.5² + w_r⟨(|RoCoF|−1)₊²⟩ + w_fast⟨(P_v−P_set)²⟩/P_b,max² + w_b⟨ΔP_b²⟩/P_b,max² + w_s⟨sat⟩/0.05 + w_v·viol", "3.23"));
C.push(P("with weights (1, 0.02, 0.5, 2, 0.1, 2, 1); the episode return is −Σc."));

C.push(H2("3.8", "DDPG and TD3 Algorithms"));
C.push(P("Both algorithms use an actor μ_θ(s) and a critic Q_φ(s, a). DDPG (Lillicrap et al., 2016) trains one critic towards the target y = r + γ Q_φ'(s', μ_θ'(s')) and updates the actor along the deterministic policy gradient. TD3 (Fujimoto et al., 2018) trains two critics and uses the smaller target, adds clipped noise to the target action, and updates the actor and the target networks less often than the critics:"));
C.push(EQ("y = r + γ min_{i=1,2} Q_φ'i (s', μ_θ'(s') + ε),     ε ~ clip(N(0, σ²), −c, c)", "3.24"));
C.push(P("Table 3.1 lists the training settings of the two studies. Networks, hyperparameters, exploration and episode seeds are identical for DDPG and TD3 within each study, so that the comparison isolates the algorithmic differences."));
C.push(...TABLE("Table 3.1 Training settings",
  ["Setting", "Study 1", "Study 2"],
  [["Networks (actor / critic)", "14→256→256→3 / 17→256→256→1, LayerNorm, ReLU", "two hidden layers of 256, ReLU; zero-initialised actor output"],
   ["Learning rates", "10⁻⁴ / 10⁻³, cosine annealing", "10⁻⁴ / 3×10⁻⁴"],
   ["γ; τ; batch", "0.99; 0.005; 128", "0.99; 0.005; 256"],
   ["Replay", "prioritised, 2×10⁵", "uniform, 10⁶"],
   ["Warm-up; update ratio", "2000 steps; 1 update per 4 steps", "10 000 steps; 1 update per 2 steps"],
   ["Exploration", "0.30 → 0.03", "0.10 → 0.03"],
   ["TD3 smoothing; clip; delay", "0.1; 0.3; 2", "0.2; 0.5; 2"],
   ["Budget", "1000 episodes × 1500 steps (20 ms), 10 seeds", "1000 episodes × 600 steps (50 ms), 5 seeds"],
   ["Model selection", "best validation return, every 10 episodes", "best validation return, every 50 episodes (untrained agent included)"]],
  [2300, 3000, 3006]));

C.push(H2("3.9", "Benchmarks, Metrics and Statistics"));
C.push(P("The learned controllers are compared with no virtual inertia, BESS droop, literature-style fixed VSGs (J, D) = (1 s, 10 pu), (4 s, 30 pu) and (15 s, 60 pu), a fixed VSG tuned on the validation data by the same objective, and rule-based adaptive VSGs in the family of Alipoor et al. (2015) and Li et al. (2017), also tuned on the validation data. Frequency regulation is measured by"));
C.push(EQ("IAE = ∫ |Δf| dt,     ISE = ∫ Δf² dt,     ITAE = ∫ t |Δf| dt", "3.25"));
C.push(P("together with the nadir, the peak RoCoF (over 100 ms and 500 ms windows), the settling time, the BESS energy throughput, the converter saturation time, the delivered headroom commitment and the time with infeasible commitments. Study 1 reports means over ten seeds with 95 % confidence intervals, one-sample t-tests against the deterministic baselines and Welch's t-test between algorithms, with Bonferroni correction. Study 2 uses paired Wilcoxon signed-rank tests over 200 test scenarios with Holm correction (Wilcoxon, 1945; Holm, 1979)."));
C.push(P("To bound the benefit of adaptation before training, a grid of fixed settings k = 1, …, K is simulated on N validation scenarios with returns R_ik. The oracle gain"));
C.push(EQ("G_oracle = (1/N) Σ_i max_k R_ik − max_k (1/N) Σ_i R_ik", "3.26"));
C.push(P("compares a scheduler that picks the best setting for each scenario with the best single setting; if G_oracle is small, no scenario-level adaptive controller can improve much on a tuned VSG."));

C.push(H2("3.10", "Validation"));
C.push(P("Two validation stages are used. First, the complete Study 2 model, including the EMS, the feasibility layer and the exported actor network, is re-implemented independently in MATLAB and compared with the Python results on identical scenarios and noise sequences. Second, a three-phase 400 V EMT model is built with Simscape Electrical (Specialized Power Systems) and an equivalent script solver: an average-model VSG converter behind its coupling impedance, the diesel SG as an internal voltage behind its reactance with swing equation, governor and AGC, the load and renewable base power as a PLL-synchronised grid-following injection, and the same controller code. The coupling reactances equal the inverse synchronising coefficients of the averaged model, so that any difference comes from what the averaged model neglects: network electromagnetics, the nonlinear power–angle relation, voltage and reactive power, the PLL and a converter power limiter acting on measured power."));

// Abbreviations and symbols (template style)
C.push(new Paragraph({ alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 240 },
  children: [new TextRun({ text: "Abbreviations and Symbols", font: FONT, size: SZ, bold: true })] }));
const SYM = [["AGC", "Automatic generation control"], ["BESS", "Battery energy storage system"], ["DDPG", "Deep deterministic policy gradient"],
  ["DRL", "Deep reinforcement learning"], ["EMS", "Energy management system"], ["EMT", "Electromagnetic transient"],
  ["IAE, ISE, ITAE", "Integral of absolute, squared and time-weighted absolute error"], ["MPPT", "Maximum power point tracking"],
  ["PLL", "Phase-locked loop"], ["PRISMA", "Preferred Reporting Items for Systematic reviews and Meta-Analyses"], ["RoCoF", "Rate of change of frequency"],
  ["SG", "Synchronous generator"], ["SoC", "State of charge"], ["TD3", "Twin delayed deep deterministic policy gradient"],
  ["VSG", "Virtual synchronous generator"], ["a_t", "Action of the agent at step t"], ["C_p", "Power coefficient of the wind turbine"],
  ["D, D_v, D_eff", "Virtual damping (declared, Study 2, after derating) (pu)"], ["Δf, Δω", "Frequency deviation (Hz, pu)"],
  ["Δf_band, Δf_max", "Frequency band edge (0.2 Hz) and deviation limit (0.5 Hz)"], ["G_oracle", "Oracle gain of adaptive scheduling"],
  ["H_sys, H_d", "Residual system inertia (Study 1); diesel inertia constant (Study 2) (s)"],
  ["h_req, h_avail, h_up, h_dn", "Required, available, upward and downward headroom (pu)"],
  ["J, J_v, J_eff", "Virtual inertia (declared, Study 2, after derating) (s)"], ["K_d, K_s", "Synchronising coefficients of diesel SG and VSG (pu)"],
  ["K_q", "Reactive droop gain (pu)"], ["P_b0", "BESS power dispatched by the EMS (pu)"], ["P_MPP, d", "PV maximum power; de-loading fraction"],
  ["P_set", "VSG power set-point (secondary control) (pu)"], ["P_v, p_vsg", "VSG active power (pu)"], ["Q_φ, μ_θ", "Critic and actor networks"],
  ["RoCoF_lim, RoCoF_max", "RoCoF limit (1 Hz/s, Study 2; 2 Hz/s, Study 1)"], ["S_base, S_rated", "Base and converter rated power"],
  ["α", "PV share of the fast VSG support"], ["γ, τ", "Discount factor; target-network update rate"], ["δ", "Angle of the virtual rotor relative to the SG rotor"]];
C.push(new Table({ width: { size: 8306, type: WidthType.DXA }, columnWidths: [2700, 5606], rows: SYM.map(([a, b]) =>
  new TableRow({ children: [
    new TableCell({ borders: noBorders, width: { size: 2700, type: WidthType.DXA }, children: [new Paragraph({ children: runs([a], 26) })] }),
    new TableCell({ borders: noBorders, width: { size: 5606, type: WidthType.DXA }, children: [new Paragraph({ children: runs([": " + b], 26) })] })] })) }));

// =====================================================================================
// CHAPTER 4  PRELIMINARY RESULTS AND DISCUSSION
// =====================================================================================
C.push(CHAP(4, "PRELIMINARY RESULTS AND DISCUSSION"));
C.push(H2("4.1", "Introduction"));
C.push(P("This chapter presents the preliminary results obtained so far. Section 4.2 summarises Study 1, the headroom-feasible DDPG and TD3 controllers for a fully converter-interfaced microgrid, whose results are reported in Khan et al. (TREC, under review) and Khan et al. (IREMOS, submitted). Section 4.3 presents Study 2, the hybrid diesel–PV–wind–BESS microgrid with Thai site data, including the oracle bound, the comparison of feasibility rules, the learned controllers and the MATLAB and EMT validation. All simulations of the learning studies were run in Python with PyTorch; validation used MATLAB R2021a and an equivalent script solver."));

C.push(H2("4.2", "Study 1: Converter-Only Microgrid"));
C.push(H3("4.2.1", "Framework and test scenarios"));
C.push(P("Fig. 4.1 shows the framework of Study 1. The agent observes the PLL-measured frequency and the plant state, proposes (J, D, K_q), and only the trained actor, the slew-rate limiter and the headroom limiter run on the converter. Fig. 4.2 shows the five test scenarios cut from the measured records and the response without virtual inertia. Without a VSG the ±0.5 Hz band is violated in every scenario: the nadir falls from 49.09 Hz on the clear day to 48.56 Hz (cloud shadow), 48.65 Hz (wind lull), 48.18 Hz (night) and 47.68 Hz (combined stress), and the 500 ms RoCoF reaches 1.83–4.58 Hz/s, above the 2 Hz/s relay limit in four of the five scenarios."));
C.push(...FIG(PF("study1_fig1.png"), 6.0, "Fig. 4.1 Headroom-feasible DDPG/TD3 framework of Study 1"));
C.push(...FIG(PF("study1_fig3.png"), 6.0, "Fig. 4.2 Measured test scenarios and the response without virtual inertia (Study 1)"));
C.push(H3("4.2.2", "Learned schedules"));
C.push(P("An initial single-seed study (Khan et al., TREC) indicated that both learned controllers reduce the integral absolute frequency error from 5.01 Hz·s without a VSG to 1.90 Hz·s (TD3), while reserving less headroom than literature-style fixed settings. To test whether this advantage survives a stricter protocol, the comparison was repeated over ten seeds per algorithm with tuned baselines (Khan et al., IREMOS). The deployed policies converge to a damping-dominated schedule: on average J = 0.46 ± 0.12 s and 0.40 ± 0.10 s and D = 21.0 ± 2.0 pu and 22.6 ± 2.3 pu for DDPG and TD3. They commit damping mainly while a disturbance is present, raising D to 35–50 pu at each contingency and lowering it once the deviation is arrested. The DDPG critic overestimates and the TD3 critic underestimates the Monte-Carlo return on every seed, and the final DDPG networks vary more between seeds."));
C.push(H3("4.2.3", "Comparison with tuned controllers"));
C.push(P("Table 4.1 summarises the comparison. Literature-style fixed settings need 0.62 pu (4 s, 30 pu) and 1.80 pu (15 s, 60 pu) of headroom, the latter equivalent to 4500 kVA on a 2500 kVA converter, and are derated in every step. On the five deterministic test windows the tuned constant VSG regulates best (IAE 1.734 Hz·s against 1.842 Hz·s for TD3), but it commits the most headroom and is derated in 40.8 % of the steps. On the 50 held-out stress episodes its advantage disappears: TD3 reaches 2.148 Hz·s against 2.180 Hz·s, and both learned controllers reserve 19–21 % less headroom on every seed (Fig. 4.3, Fig. 4.4)."));
C.push(...TABLE("Table 4.1 Study 1 results (learned controllers: mean ± 95 % CI over ten seeds)",
  ["Controller", "IAE (Hz·s)", "Nadir (Hz)", "RoCoF (Hz/s)", "Reserve (pu)", "Derated (%)"],
  [[{ t: "Five test windows", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }],
   ["No VSG", "8.871", "48.43", "3.12", "0.000", "0"],
   ["Fixed low (1, 10)", "3.670", "49.59", "0.81", "0.180", "0"],
   ["Fixed high (4, 30)", "2.657", "49.74", "0.54", "0.382", "100"],
   ["Fixed max (15, 60)", "3.335", "49.67", "0.59", "0.380", "100"],
   ["Fixed tuned (0, 35)", "1.734", "49.80", "0.42", "0.333", "40.8"],
   ["Rule-based adaptive", "1.857", "49.79", "0.44", "0.244", "10.2"],
   ["DDPG-VSG", "1.909 ± 0.075", "49.80", "0.43", "0.243 ± 0.015", "9.9 ± 3.5"],
   ["TD3-VSG", "1.842 ± 0.073", "49.81", "0.42", "0.253 ± 0.019", "14.6 ± 6.2"],
   [{ t: "Held-out stress test (50 episodes)", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }, { t: "", fill: "F2F2F2" }],
   ["No VSG", "12.346", "48.04", "4.01", "0.000", "0"],
   ["Fixed tuned (0, 35)", "2.180", "49.77", "0.49", "0.342", "20.1"],
   ["Rule-based adaptive", "2.278", "49.76", "0.52", "0.256", "7.6"],
   ["DDPG-VSG", "2.204 ± 0.061", "49.78", "0.49", "0.270 ± 0.014", "12.2 ± 2.9"],
   ["TD3-VSG", "2.148 ± 0.067", "49.79", "0.47", "0.275 ± 0.018", "14.5 ± 4.1"]],
  [2400, 1300, 1050, 1150, 1250, 1156]));
NOTE("Fixed settings are (J [s], D [pu]). Reserve: delivered headroom commitment, Eq. (3.17) with J_eff and D_eff. Source: Khan et al. (IREMOS).");
C.push(...FIG(PF("study1_fig5.png"), 6.0, "Fig. 4.3 DDPG, TD3 and non-learning controllers in Study 1: training, validation, critic bias, frequency, RoCoF and voltage"));
C.push(...FIG(PF("study1_fig6.png"), 6.0, "Fig. 4.4 Regulation against converter cost in Study 1: IAE against delivered headroom"));
C.push(P("Two lessons from Study 1 shape the rest of the thesis. Once feasibility is enforced, learning moves the controller along a trade-off between regulation and reserved headroom rather than dominating a tuned design; and because one second of inertia costs as much headroom as 8 pu of damping, headroom-limited VSG control is mainly a damping-scheduling problem. Both lessons raise the question of how large the benefit of adaptation can be in a system that also has physical inertia, which Study 2 addresses."));

C.push(H2("4.3", "Study 2: Hybrid Microgrid with Thai Site Data"));
C.push(H3("4.3.1", "Test system and data"));
C.push(P("Fig. 4.5 shows the hybrid microgrid of Study 2. The 2024 data for Nakhon Ratchasima give a low-wind site (ERA5 mean 4.2 m/s at 100 m, capacity factor 9.5 % for the class III turbine) with a PV capacity factor of 17.3 % (Table 4.2, Fig. 4.6). The EMS dispatch takes part of the BESS capability, most visibly during the evening peak, so the headroom available for synthetic inertia varies widely over the year; operating points at which the load could not be served are screened out (7.4 % of test draws)."));
C.push(...FIG(PF("fig_single_line.png"), 5.6, "Fig. 4.5 Hybrid diesel–PV–wind–BESS microgrid of Study 2"));
C.push(...TABLE("Table 4.2 Operating-point data of Study 2 (2024) by subset",
  ["Subset", "Hours", "Wind (m/s)", "Wind CF", "PV CF", "GHI (W/m²)", "Load (MW)", "RES share"],
  [["All", "8777", "4.19", "9.5 %", "17.3 %", "213", "0.64", "36 %"],
   ["Training", "6425", "4.38", "10.5 %", "17.2 %", "212", "0.64", "37 %"],
   ["Validation", "1176", "3.71", "7.7 %", "17.1 %", "211", "0.64", "33 %"],
   ["Test", "1176", "3.67", "6.3 %", "18.1 %", "223", "0.64", "32 %"]],
  [1150, 850, 1050, 950, 950, 1150, 1100, 1106]));
C.push(...FIG(RF("fig_data_overview.png"), 5.6, "Fig. 4.6 Daily means of the hourly operating points of Study 2 (validation and test weeks shaded)"));
C.push(H3("4.3.2", "Oracle bound"));
C.push(P("On 40 validation scenarios the best single fixed setting (J_v = 3 s, D_v = 15 pu) reaches an objective return of −94.66, and the per-scenario oracle of (3.26) reaches −92.66: adaptive scheduling can improve the objective by at most 2.0 points, or 2.1 %. The damping chosen by the oracle hardly depends on the headroom (12–15 pu from the lowest to the highest headroom tercile). The margin is small because the synchronous coupling of (3.12) gives the VSG about 71 % of every step regardless of its parameters, and secondary control restores the frequency within 10–20 s, leaving J_v and D_v only a short part of each event to shape."));
C.push(H3("4.3.3", "Comparison of feasibility rules"));
C.push(P("Table 4.3 and Fig. 4.7 apply the feasibility rules to fixed settings on 200 test scenarios. Without a constraint, the 'Fixed high' setting of Study 1 (4 s, 30 pu) needs more headroom than is available for 5.3 s of every 30 s episode, and the largest setting (8 s, 50 pu) for 17.6 s, confirming in a system with physical inertia that literature-style gains are frequently undeliverable. Proportional derating, the method of Study 1, gives lower converter saturation than clipping for every setting (paired Wilcoxon, p < 10⁻⁴) and a higher return for the standard, high and largest settings. The summed requirement (3.17) is more conservative than the time-separated requirement (3.21): with the same limits it reduces saturation and BESS energy further but deepens the nadir, and with the wider limits of Study 1 (0.5 Hz, 2 Hz/s) it reduces every setting to about J_v ≈ 2 s and D_v ≈ 11–15 pu, so that higher declared gains no longer change the response."));
C.push(...TABLE("Table 4.3 Feasibility rules applied to fixed settings (means over 200 test scenarios)",
  ["Setting (J_v, D_v)", "Rule", "Saturation (s)", "Nadir (Hz)", "BESS (kWh)", "Infeasible (s)", "Return"],
  [["Tuned (3, 15)", "None", "0.103", "0.573", "0.775", "2.330", "−105.9"],
   ["", "Max, clip", "0.123", "0.573", "0.775", "0.007", "−106.1"],
   ["", "Max, scale", "0.097", "0.574", "0.772", "0.008", "−105.1"],
   ["", "Sum, scale", "0.090", "0.589", "0.764", "0.008", "−105.7"],
   ["", "Sum, scale, wide", "0.073", "0.783", "0.702", "0.011", "−123.1"],
   ["High (4, 30)", "None", "0.140", "0.434", "0.918", "5.256", "−137.1"],
   ["", "Max, clip", "0.146", "0.432", "0.914", "0.012", "−134.5"],
   ["", "Max, scale", "0.129", "0.432", "0.909", "0.011", "−132.5"],
   ["", "Sum, scale", "0.112", "0.474", "0.868", "0.012", "−126.1"],
   ["Largest (8, 50)", "None", "0.137", "0.371", "1.026", "17.630", "−169.9"],
   ["", "Max, clip", "0.146", "0.368", "1.006", "0.037", "−161.8"],
   ["", "Max, scale", "0.112", "0.397", "0.963", "0.034", "−152.9"],
   ["", "Sum, scale", "0.100", "0.478", "0.874", "0.025", "−133.8"]],
  [1500, 1350, 1100, 1000, 1050, 1150, 1156]));
NOTE("Infeasible: time per 30 s episode at which the applied pair violates (3.21). Wide: limits of Study 1 (0.5 Hz, 2 Hz/s).");
C.push(...FIG(RF("fig_headroom_ablation.png"), 6.0, "Fig. 4.7 Feasibility rules applied to five fixed settings: saturation, nadir and objective return"));
C.push(H3("4.3.4", "Learned controllers"));
C.push(P("Residual TD3 and DDPG agents were trained for 1000 episodes on five seeds each, with and without the feasibility constraint, and evaluated on 200 test scenarios (Table 4.4). Without fast support the diesel-only system collapses in 97.5 % of the scenarios, and BESS droop without inertia keeps the system stable but at a RoCoF of 5.5 Hz/s. The tuned fixed VSG achieves the best objective return, and for all ten learned runs the best validation checkpoint was the untrained agent, that is, the tuned VSG itself. The final TD3 policies reduce the nadir by 0.061 Hz but use 0.067 kWh more BESS energy per episode, a different point on the same trade-off; DDPG is worse than TD3 on nadir, RoCoF and return. Trained without the constraint, TD3 holds an undeliverable pair for 5.07 s of every episode, more than twice the 2.33 s of the tuned VSG; with the constraint this falls to 0.02 s (p ≈ 10⁻³²)."));
C.push(...TABLE("Table 4.4 Study 2 test results (200 scenarios; learned controllers averaged over five seeds)",
  ["Controller", "Nadir (Hz)", "RoCoF (Hz/s)", "BESS (kWh)", "Infeasible (s)", "Return"],
  [["Fixed VSG, tuned (3 s, 15 pu)", "0.573", "1.474", "0.775", "2.330", "−105.9"],
   ["Fixed VSG, tuned + constraint", "0.573", "1.479", "0.775", "0.007", "−106.1"],
   ["Fixed VSG, standard (3 s, 20 pu)", "0.508", "1.452", "0.934", "2.340", "−115.8"],
   ["Bang-bang VSG", "0.505", "1.423", "0.936", "2.989", "−116.4"],
   ["TD3, final policy", "0.522", "1.482", "0.849", "0.019", "−122.0"],
   ["TD3 without constraint, final", "0.540", "1.457", "0.832", "5.069", "−124.2"],
   ["DDPG, final policy", "0.596", "1.594", "0.845", "0.022", "−133.4"],
   ["BESS droop (no inertia)", "0.732", "5.520", "0.927", "1.103", "−286.8"],
   ["Diesel only", "3.06*", "7.38", "0", "0", "−557.7"]],
  [2906, 1000, 1100, 1050, 1150, 1100]));
NOTE("*97.5 % of the episodes collapse. Nadir is the worst-event frequency deviation.");
C.push(...FIG(RF("fig_response_sc32.png"), 4.6, "Fig. 4.8 Test scenario 32 of Study 2: frequency, RoCoF, VSG power and scheduled virtual inertia"));
C.push(...FIG(RF("fig_pareto.png"), 6.0, "Fig. 4.9 Controllers against the family of fixed settings and its attainable front (Study 2)"));
C.push(H3("4.3.5", "Validation"));
C.push(P("The MATLAB re-implementation reproduces the Python results exactly for the fixed controllers and within 1.1 × 10⁻⁷ Hz for the TD3 policy, a difference caused by single-precision arithmetic in the network (Table 4.5). In the three-phase EMT model, the frequency follows the averaged model with an RMS difference of 0.014–0.018 Hz over twelve scenarios and three controllers, the nadir agrees within 0.2 % for the fixed controllers and is 4 % deeper for TD3, and the BESS energy agrees within 0.8 % (Fig. 4.10). Two differences are physical. At each load step the bus-voltage phase jumps by about 3°, which a PLL reads as a brief frequency spike, so the 100 ms RoCoF is about 2.5 times higher than in the averaged model, while the 500 ms RoCoF differs by only 3–11 %; and the converter limiter, acting on measured power, is active 2.3–2.7 times longer. The ranking of the controllers is the same in both models. ", TODO("AUTHOR: confirm the EMT results with the Simscape Electrical model in MATLAB R2021a")));
C.push(...TABLE("Table 4.5 Validation summary (12 test scenarios × 3 controllers)",
  ["Check", "Quantity", "Result"],
  [["MATLAB vs Python", "max |ΔΔf|, fixed / constrained / TD3", "0 / 0 / 1.1 × 10⁻⁷ Hz"],
   ["EMT vs averaged model", "RMS difference of Δf", "0.014–0.018 Hz"],
   ["EMT vs averaged model", "Worst-event nadir", "fixed: within 0.2 %; TD3: 4 % deeper"],
   ["EMT vs averaged model", "BESS energy", "within 0.8 %"],
   ["EMT vs averaged model", "RoCoF over 100 ms / 500 ms", "× 2.5 / +3 to +11 %"],
   ["EMT vs averaged model", "Converter saturation time", "× 2.3–2.7 (same ordering)"],
   ["EMT, constrained controllers", "Infeasible commitments", "≤ 0.03 s per episode"]],
  [2500, 3200, 2606]));
C.push(...FIG(RF("fig_emt_validation.png"), 6.0, "Fig. 4.10 Averaged (RMS) and three-phase EMT models for test scenario 1"));

C.push(H2("4.4", "Discussion of Preliminary Results"));
C.push(P("The two studies point in the same direction. The feasibility constraint is the robust contribution: in both systems, high-gain VSG settings and unconstrained learned policies commit inertia and damping that the converter cannot deliver, and the constraint removes these commitments at negligible cost for a well-tuned VSG. The benefit of learning depends on the system. In the converter-only microgrid, learning buys about one fifth less reserved headroom at equal regulation on unseen stress episodes; in the hybrid microgrid, where a synchronous machine shares every step and secondary control is fast, the oracle shows that there is little to gain, and the learned agents do not beat the tuned VSG on the objective. Across the studies, damping matters more than inertia, proportional derating is preferable to clipping, and averaged models are adequate for training and ranking controllers but underestimate PLL-measured RoCoF and limiter activity."));

// =====================================================================================
// CHAPTER 5  CONCLUSION AND FUTURE WORK PLAN
// =====================================================================================
C.push(CHAP(5, "CONCLUSION AND FUTURE WORK PLAN"));
C.push(H2("5.1", "Conclusion"));
C.push(P("This proposal presents a thesis on feasible synthetic inertia for low-inertia PV–wind–BESS microgrids. A converter-headroom feasibility constraint has been formulated that limits the virtual inertia and damping of a VSG to the power the BESS and a de-loaded PV plant can deliver, and DDPG and TD3 agents have been trained to schedule the VSG parameters under it in two systems. The preliminary results show that (i) literature-style high-gain VSG settings require far more headroom than the converter can reserve and are derated almost continuously; (ii) in a converter-only microgrid, learned controllers match the regulation of a tuned constant VSG on unseen stress episodes while reserving 19–21 % less headroom, and DDPG and TD3 perform alike once checkpoints are selected on validation data; (iii) in a hybrid microgrid with physical inertia, the oracle bound limits the gain of any adaptive scheduler to 2.1 %, the learned agents do not exceed a tuned VSG on the objective, and the constraint cuts the undeliverable commitments of a learned policy from 5.07 s to 0.02 s per 30 s episode; and (iv) an independent MATLAB implementation and a three-phase EMT model confirm the averaged-model results, apart from PLL-measured RoCoF spikes and longer limiter activity at circuit level."));
C.push(H2("5.2", "Future Work"));
C.push(P("The remaining work will complete the four objectives of the thesis:"));
{ const L = newList();
  C.push(L("Retrain the Study 2 agents with the time-separated requirement and proportional derating, which the rule comparison identified as the best feasibility layer, and repeat the evaluation."));
  C.push(L("Confirm the EMT results with the Simscape Electrical model in MATLAB R2021a and extend the circuit-level validation to the converter-only system of Study 1."));
  C.push(L("Study the sensitivity of the conclusions to the reward weights and apply the oracle bound to systems with weaker grid-forming coupling and slower secondary control, where adaptive control is expected to pay off more."));
  C.push(L("Replace the synthetic load profile with measured Thai load data if available, and complete the systematic literature search (Section 2.2) with the database counts."));
  C.push(L("Prepare the journal publications and write the thesis.")); }
C.push(H2("5.3", "Research Schedule"));
C.push(P("Table 5.1 shows the planned schedule. Months are counted from the approval of this proposal."));
const DONE = "A9D18E", PLAN = "9DC3E6";
const gantt = (task, status, months, fill) => [task, status, ...Array.from({ length: 12 }, (_, i) =>
  months.includes(i + 1) ? { t: "", fill } : "")];
C.push(...TABLE("Table 5.1 Research schedule", ["Task", "Status", ...Array.from({ length: 12 }, (_, i) => `${i + 1}`)],
  [gantt("Study 1: models, DRL, evaluation", "Done", [], DONE),
   gantt("Study 2: models, data, DRL, oracle", "Done", [], DONE),
   gantt("Feasibility-rule comparison; MATLAB and EMT validation", "Done", [], DONE),
   gantt("PRISMA search counts and literature update", "Planned", [1, 2], PLAN),
   gantt("Retraining with proportional derating", "Planned", [1, 2, 3], PLAN),
   gantt("Simscape Electrical confirmation", "Planned", [1, 2, 3], PLAN),
   gantt("Sensitivity and weak-coupling studies", "Planned", [3, 4, 5, 6], PLAN),
   gantt("Journal publications", "Ongoing", [1, 2, 3, 4, 5, 6, 7, 8], PLAN),
   gantt("Thesis writing", "Planned", [6, 7, 8, 9, 10, 11], PLAN),
   gantt("Thesis defence", "Planned", [12], PLAN)],
  [2706, 900, ...Array(12).fill(475)], { size: 20 }));
NOTE("Green: completed before the proposal; blue: planned. " + "Map months to the academic calendar: [AUTHOR]");
C.push(H2("5.4", "Expected Publications"));
{ const L = newList();
  C.push(L("M. B. Khan, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Reinforcement learning based virtual synchronous generator control for a low inertia solar–wind–BESS microgrid: A converter headroom-feasible approach,” under review (TREC)."));
  C.push(L("M. B. Khan, P. Pao-La-Or, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, “Headroom-feasible adaptive virtual synchronous generator control with deep reinforcement learning: A multi-seed comparison with tuned controllers,” to be submitted to the International Review on Modelling and Simulations (IREMOS)."));
  C.push(L("M. B. Khan et al., “Bounding the benefit of learned virtual-inertia scheduling in a hybrid diesel–PV–wind–BESS microgrid: Oracle analysis, headroom projection and circuit-level validation,” in preparation for the International Journal on Engineering Applications (IREA).")); }

// =====================================================================================
// REFERENCES
// =====================================================================================
const REFS = [
  "R. Agarwal, M. Schwarzer, P. S. Castro, A. C. Courville and M. Bellemare, Deep reinforcement learning at the edge of the statistical precipice, Advances in Neural Information Processing Systems, vol. 34, pp. 29304-29320, 2021.",
  "M. A. Afifi, M. I. Marei and A. M. Mohamad, Reinforcement learning approach with deep deterministic policy gradient DDPG-controlled virtual synchronous generator for an islanded microgrid, in 2023 24th International Middle East Power System Conference (MEPCON), 2023.",
  "J. Alipoor, Y. Miura and T. Ise, Power system stabilization using virtual synchronous generator with alternating moment of inertia, IEEE Journal of Emerging and Selected Topics in Power Electronics, vol. 3, no. 2, pp. 451-458, 2015.",
  "H. Bevrani, T. Ise and Y. Miura, Virtual synchronous generators: A survey and new perspectives, International Journal of Electrical Power & Energy Systems, vol. 54, pp. 244-254, 2014.",
  "E. Cheynet, Post-processed time series at FINO1 in 2007, Zenodo, 2025.",
  "A. Criollo et al., Enhancing virtual inertia control in microgrid clusters: A novel frequency response model based on deep reinforcement learning, Applied Sciences, vol. 16, no. 13, p. 6685, 2026.",
  "O. E. Egbomwan, S. Liu and H. Chaoui, Twin delayed deep deterministic policy gradient (TD3) based virtual inertia control for inverter-interfacing DGs in microgrids, IEEE Systems Journal, vol. 17, no. 2, pp. 2122-2132, 2023.",
  "O. E. Egbomwan et al., Learning-based predictive virtual inertia control for frequency regulation in low inertia power grids, IEEE Open Journal of Circuits and Systems, vol. 6, pp. 504-519, 2025.",
  "S. Fujimoto, H. van Hoof and D. Meger, Addressing function approximation error in actor-critic methods, in Proceedings of the 35th International Conference on Machine Learning (ICML), 2018.",
  "M. Glavic, (Deep) reinforcement learning for electric power system control and related problems: A short review and perspectives, Annual Reviews in Control, vol. 48, pp. 22-35, 2019.",
  "J. Han et al., Adaptive VSG control strategy considering energy storage SOC constraints, Frontiers in Energy Research, vol. 11, p. 1278648, 2023.",
  "P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup and D. Meger, Deep reinforcement learning that matters, in Proceedings of the AAAI Conference on Artificial Intelligence, 2018.",
  "H. Hersbach et al., The ERA5 global reanalysis, Quarterly Journal of the Royal Meteorological Society, vol. 146, no. 730, pp. 1999-2049, 2020.",
  "S. Holm, A simple sequentially rejective multiple test procedure, Scandinavian Journal of Statistics, vol. 6, no. 2, pp. 65-70, 1979.",
  "IEC 61400-12-1:2017, Wind energy generation systems - Part 12-1: Power performance measurements of electricity producing wind turbines, International Electrotechnical Commission, 2017.",
  "M. B. Khan, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, Reinforcement learning based virtual synchronous generator control for a low inertia solar-wind-BESS microgrid: A converter headroom-feasible approach, under review (TREC).",
  "M. B. Khan, P. Pao-La-Or, A. Srikaew, T. Ratniyomchai, J. Polprasert and A. Oonsivilai, Headroom-feasible adaptive virtual synchronous generator control with deep reinforcement learning: A multi-seed comparison with tuned controllers, manuscript to be submitted (IREMOS).",
  "P. Kundur, Power System Stability and Control, New York: McGraw-Hill, 1994.",
  "D. Li et al., A self-adaptive inertia and damping combination control of VSG to support frequency stability, IEEE Transactions on Energy Conversion, vol. 32, no. 1, pp. 397-398, 2017.",
  "J. Li et al., Adaptive VSG control method based on reinforcement learning strategy optimization, Electric Power Systems Research, vol. 257, p. 112997, 2026.",
  "T. P. Lillicrap et al., Continuous control with deep reinforcement learning, in International Conference on Learning Representations (ICLR), 2016.",
  "C. Lu and X. Zhuan, Adaptive control for virtual synchronous generator parameters based on soft actor critic, Sensors, vol. 24, no. 7, p. 2035, 2024.",
  "F. Milano, F. Dörfler, G. Hug, D. J. Hill and G. Verbič, Foundations and challenges of low-inertia systems, in 2018 Power Systems Computation Conference (PSCC), 2018.",
  "W. B. Mol, W. H. Knap and C. C. van Heerwaarden, Ten years of 1 Hz solar irradiance observations at Cabauw, the Netherlands, with cloud observations, variability classifications, and statistics, Earth System Science Data, vol. 15, no. 5, pp. 2139-2151, 2023.",
  "NASA Prediction Of Worldwide Energy Resources (POWER) Project, hourly data, https://power.larc.nasa.gov.",
  "O. Oboreh-Snapps et al., Virtual synchronous generator control using twin delayed deep deterministic policy gradient method, IEEE Transactions on Energy Conversion, vol. 39, no. 1, pp. 214-228, 2024.",
  "M. J. Page et al., The PRISMA 2020 statement: An updated guideline for reporting systematic reviews, BMJ, vol. 372, n71, 2021.",
  "A. D. Paquette and D. M. Divan, Virtual impedance current limiting for inverters in microgrids with synchronous generators, IEEE Transactions on Industry Applications, vol. 51, no. 2, pp. 1630-1638, 2015.",
  "T. Qoria et al., Current limiting algorithms and transient stability analysis of grid-forming VSCs, Electric Power Systems Research, vol. 189, p. 106726, 2020.",
  "T. Shi et al., Research on adaptive optimal control strategy of virtual synchronous generator inertia and damping parameters, IET Power Electronics, vol. 17, no. 1, pp. 121-133, 2024.",
  "T. Silver, K. Allen, J. Tenenbaum and L. Kaelbling, Residual policy learning, arXiv:1812.06298, 2018.",
  "E. Skoplaki and J. A. Palyvos, On the temperature dependence of photovoltaic module electrical performance: A review of efficiency/power correlations, Solar Energy, vol. 83, no. 5, pp. 614-624, 2009.",
  "J. Slootweg, S. de Haan, H. Polinder and W. Kling, General model for representing variable speed wind turbines in power system dynamics simulations, IEEE Transactions on Power Systems, vol. 18, no. 1, pp. 144-151, 2003.",
  "R. S. Sutton and A. G. Barto, Reinforcement Learning: An Introduction, 2nd ed., Cambridge, MA: MIT Press, 2018.",
  "A. Ulbig, T. S. Borsche and G. Andersson, Impact of low rotational inertia on power system stability and operation, IFAC Proceedings Volumes, vol. 47, no. 3, pp. 7290-7297, 2014.",
  "F. Wilcoxon, Individual comparisons by ranking methods, Biometrics Bulletin, vol. 1, no. 6, pp. 80-83, 1945.",
  "Q.-C. Zhong and G. Weiss, Synchronverters: Inverters that mimic synchronous generators, IEEE Transactions on Industrial Electronics, vol. 58, no. 4, pp. 1259-1267, 2011.",
];
C.push(UNNUM("REFERENCES"));
REFS.forEach((r) => C.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 120, line: 300 },
  indent: { left: 720, hanging: 720 }, children: runs([r], 26) })));

C.push(UNNUM("APPENDIX"));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: runs([B("List of manuscripts arising from this research")]) }));
C.push(PN("A. Khan et al., “Reinforcement learning based virtual synchronous generator control for a low inertia solar–wind–BESS microgrid: A converter headroom-feasible approach” (TREC), under review."));
C.push(PN("B. Khan et al., “Headroom-feasible adaptive virtual synchronous generator control with deep reinforcement learning: A multi-seed comparison with tuned controllers” (IREMOS), to be submitted."));
C.push(PN("C. Khan et al., “Bounding the benefit of learned virtual-inertia scheduling in a hybrid diesel–PV–wind–BESS microgrid: Oracle analysis, headroom projection and circuit-level validation” (IREA), in preparation."));
C.push(PN(TODO("AUTHOR: attach the full manuscripts here, as in the template")));

// =====================================================================================
// DOCUMENT
// =====================================================================================
const pageHeader = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 24 })] })] });
const PAGE = { size: { width: 11906, height: 16838 }, margin: { top: 2160, bottom: 1440, left: 2160, right: 1440, header: 720 } };
const doc = new Document({
  creator: "Muhammad Binyameen Khan", title: "Thesis proposal",
  features: { updateFields: true },
  styles: { default: { document: { run: { font: FONT, size: SZ } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: FONT }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: SZ, bold: true, font: FONT }, paragraph: { outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: SZ, bold: true, italics: true, font: FONT }, paragraph: { outlineLevel: 2 } }] },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] },
    ...numRefs.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1)", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] }))] },
  sections: [
    { properties: { page: PAGE }, headers: { default: new Header({ children: [new Paragraph({ children: [] })] }) }, children: cover },
    { properties: { page: { ...PAGE, pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN } } },
      headers: { default: pageHeader },
      children: [...front,
        new Paragraph({ children: [new PageBreak()] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
          children: [new TextRun({ text: "TABLE OF CONTENT", font: FONT, size: 32, bold: true })] }),
        new TableOfContents("Table of Content", { hyperlink: true, headingStyleRange: "1-2" })] },
    { properties: { page: { ...PAGE, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } },
      headers: { default: pageHeader }, children: C },
  ],
});
Packer.toBuffer(doc).then((b) => { const out = path.join(__dirname, "Thesis_Proposal_MB_Khan.docx"); fs.writeFileSync(out, b); console.log("wrote", out); });
