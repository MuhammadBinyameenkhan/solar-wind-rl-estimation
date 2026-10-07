"""
Single source of truth for every constant, with units.

Test system (paper Section 3.1): 50 Hz, 100 % inverter-interfaced microgrid at
Nakhon Ratchasima, Thailand -- 500 kW PV, 500 kW Type-4 PMSG wind turbine,
2500 kVA grid-forming BESS operated as a VSG, 1800 kW load.

Other modules read these values as attributes at CALL time
(``from . import config as C`` then ``C.F_NOM``), so run-time overrides such as
``--hz 60`` or ``--episodes 300`` really do propagate everywhere.
"""
import os

# ----------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------
SEED = 0
DEFAULT_SEEDS = (0, 1, 2, 3, 4)       # multi-seed study (paper Section 4.7)

# ----------------------------------------------------------------
# Output locations (created lazily, never at import time)
# ----------------------------------------------------------------
OUT_DIR = os.environ.get("VSG_OUT_DIR", "results")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SAVE_PANELS = True


def out_path(*parts) -> str:
    path = os.path.join(OUT_DIR, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


# ================================================================
# 1. POWER SYSTEM
# ================================================================
S_BASE = 2500e3          # VA   converter / per-unit base
P_LOAD_NOM = 1800e3      # W    nominal active load
PF_LOAD = 0.95           # -    lagging
Q_STEP_RATIO = 2.5       # -    contingency is motor-like (Q step = 2.5 x P step)

F_NOM = 50.0             # Hz
V_NOM = 1.0              # pu

H_SYS = 0.5              # s    residual physical inertia (no synchronous machines)

# Primary frequency response.  In a 100 % inverter microgrid the only
# dispatchable converter is the BESS, so the droop is part of the BESS
# setpoint and counts against its rating and headroom (no phantom source).
K_DROOP = 10.0           # pu/pu  (1/R, 10 % droop)
T_DROOP = 0.5            # s      first-order lag of the droop loop

TAU_AGC = 1.0            # s    BESS schedule tracks filtered renewable output

X_TH = 0.25              # pu   Thevenin reactance at the PCC
T_VOLT = 0.10            # s    voltage-loop time constant
KQ_VSG = 8.0             # pu   default Q-V droop gain (fixed controllers)
LOAD_V_EXP = 1.0         # -    active-load voltage exponent

# ----------------------------------------------------------------
# Battery
# ----------------------------------------------------------------
E_BESS_WH = 1.25e6       # Wh   1250 kWh
SOC_INIT = 0.50
SOC_MIN = 0.10
SOC_MAX = 0.95
ETA_BESS = 0.96          # round trip (sqrt applied one way)

# ----------------------------------------------------------------
# Actuator and measurement
# ----------------------------------------------------------------
SLEW_TIME = 0.30         # s    full-range traverse time for J, D, Kq
PLL_TAU = 0.02           # s
PLL_NOISE_HZ = 0.008     # Hz   1-sigma
ROCOF_FILT_TAU = 0.05    # s

# ----------------------------------------------------------------
# Grid-code limits
# ----------------------------------------------------------------
F_BAND_OK = 0.5          # Hz   operational band  (= df_max in Eq. 20)
ROCOF_LIMIT = 2.0        # Hz/s relay threshold   (= RoCoF_max in Eq. 20)
ROCOF_WINDOW = 0.5       # s    relay averaging window
F_TRIP_MARGIN = 3.0      # Hz
V_TRIP_LO, V_TRIP_HI = 0.80, 1.20


def f_trip():
    return F_NOM - F_TRIP_MARGIN, F_NOM + F_TRIP_MARGIN


def set_nominal_frequency(hz: float) -> None:
    global F_NOM
    F_NOM = float(hz)


# ================================================================
# 2. SOLAR PV
# ================================================================
PV_RATED = 500e3
PV_G_REF = 1000.0
PV_T_REF = 25.0
PV_T_COEFF = 0.0045
PV_NOCT_RISE = 0.030
PV_DEGRADATION = 0.995

# ================================================================
# 3. WIND TURBINE (Type-4 PMSG)
# ================================================================
WT_RATED = 500e3
WT_RHO = 1.225
WT_RADIUS = 18.9         # m  -> exactly 500 kW at 11.5 m/s with Cp_max = 0.48
WT_V_CUTIN = 3.0
WT_V_RATED = 11.5
WT_V_CUTOUT = 25.0
WT_LAMBDA_OPT = 8.1
WT_H = 4.0
WT_TAU_CONV = 0.02

# ================================================================
# 4. TIMING
# ================================================================
CONTROL_DT = 0.02        # s   agent decision period
PHYS_SUBSTEPS = 10       # physics at 2 ms
EPISODE_DURATION = 30.0  # s


def max_steps() -> int:
    return int(round(EPISODE_DURATION / CONTROL_DT))     # 1500


# ================================================================
# 5. RL PROBLEM
# ================================================================
# Observation (14):
#   df/0.5, RoCoF/2, t/T, P_pv/rated, P_w/rated, v_w/25, G/1000, SOC,
#   (V-1)/0.1, P_bess/S, J/J_MAX, D/D_MAX, Kq_norm, h_avail
#   The last four are new: J, D and Kq are slew-limited, so the parameters
#   actually in force are part of the plant state and must be observed;
#   h_avail is what the feasibility constraint is evaluated against.
STATE_DIM = 14
ACTION_DIM = 3           # [J, D, Kq]
J_MIN, J_MAX = 0.05, 15.0     # s
D_MIN, D_MAX = 5.0, 60.0      # pu
KQ_MIN, KQ_MAX = 2.0, 20.0    # pu


def action_bounds():
    return [(J_MIN, J_MAX), (D_MIN, D_MAX), (KQ_MIN, KQ_MAX)][:ACTION_DIM]


# --- Reward weights (fixed a priori; see README "Reward") ----------
W_FREQ = 25.0            # (df in Hz)^2
W_ROCOF = 10.0           # (RoCoF / 2 Hz/s)^2
W_VOLT = 6.0             # (dV / 0.05 pu)^2
W_EFFORT = 5.0           # mean squared change of the normalised action
W_SOC = 2.0              # |SOC - 0.5|
W_BESS = 0.3             # (P_vsg / S)^2
W_RESERVE = 0.5          # x h_req in pu (Eq. 22) -- the same quantity reported
W_INFEAS = 8.0           # max(0, h_req - h_avail)
R_ALIVE = 1.0
R_TERM_PENALTY = 100.0

# ================================================================
# 6. TRAINING (identical for DDPG and TD3)
# ================================================================
EPISODES = 1000
BATCH_SIZE = 128
GAMMA = 0.99
TAU_SOFT = 0.005
LR_ACTOR = 1e-4
LR_CRITIC = 1e-3
WEIGHT_DECAY = 1e-5
HIDDEN = 256
WARMUP_STEPS = 2000
UPDATE_EVERY = 4
GRAD_CLIP = 1.0
LR_ANNEAL = True

EXPL_NOISE_START = 0.30
EXPL_NOISE_END = 0.03
NOISE_DECAY_FRACTION = 0.8

POLICY_NOISE = 0.2
NOISE_CLIP = 0.5
POLICY_FREQ = 2

PER_CAPACITY = 200_000
PER_ALPHA = 0.6
PER_BETA_START = 0.4
PER_BETA_END = 1.0
PER_EPS = 1e-5

EVAL_EVERY = 10
CONV_WINDOW = 5
CONV_TOL = 0.02

# ----------------------------------------------------------------
# Data splits -- training, model selection and testing never overlap.
#   train       stochastic episodes, seed = run_seed*100_000 + episode
#   validation  N_VAL stochastic episodes, seeds VAL_SEED0 + i   (model
#               selection for RL AND tuning of the fixed / heuristic baselines)
#   test        the five deterministic paper scenarios (TEST_SEED)
#               + N_STRESS randomised held-out episodes (STRESS_SEED0 + i)
# ----------------------------------------------------------------
N_VAL = 10
VAL_SEED0 = 50_000
TEST_SEED = 70_007
N_STRESS = 50
STRESS_SEED0 = 90_000

EVAL_SCENARIOS = ["clear", "cloud", "wind_drop", "night", "combined"]
CURRICULUM = [
    (0.30, ["clear", "cloud"]),
    (0.60, ["clear", "cloud", "wind_drop", "night"]),
    (1.00, ["clear", "cloud", "wind_drop", "night", "combined"]),
]

RAND_STEP_FRAC = (0.08, 0.32)
RAND_JITTER = 0.25
LOAD_EVENTS = ((0.20, 0.45, 1.00), (0.62, 0.82, -0.60))
LOAD_STEP_RAMP = 0.10
LOAD_STEP = {"clear": 0.10, "cloud": 0.15, "wind_drop": 0.15,
             "night": 0.20, "combined": 0.25}


def event_windows():
    return [(a * EPISODE_DURATION, b * EPISODE_DURATION) for a, b, _ in LOAD_EVENTS]


# ================================================================
# 7. BASELINE CONTROLLERS
# ================================================================
#   none / fixed_low / fixed_high / fixed_max  -- the paper's originals
#   fixed_tuned   best constant (J, D, Kq) on the VALIDATION set, chosen by the
#                 same reward the agents maximise (fair, data-split-clean)
#   adaptive_rule rule-based adaptive VSG (Alipoor 2014 / Li 2016 family),
#                 its gains tuned the same way
BASELINES = {
    "none":       dict(J=0.0, D=0.0),
    "fixed_low":  dict(J=1.0, D=10.0),
    "fixed_high": dict(J=4.0, D=30.0),
    "fixed_max":  dict(J=15.0, D=60.0),
}
TUNED_BASELINES = ["fixed_tuned", "adaptive_rule"]
FIXED_GRID_J = [0.0, 0.5, 1.0, 2.0, 4.0]
FIXED_GRID_D = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
FIXED_GRID_KQ = [8.0, 14.0, 20.0]

CONTROLLERS = ["none", "fixed_low", "fixed_high", "fixed_max",
               "fixed_tuned", "adaptive_rule", "ddpg", "td3"]
CONTROLLER_LABELS = {
    "none": "No VSG", "fixed_low": "Fixed low", "fixed_high": "Fixed high",
    "fixed_max": "Fixed max", "fixed_tuned": "Fixed tuned",
    "adaptive_rule": "Rule-based adaptive", "ddpg": "DDPG-VSG", "td3": "TD3-VSG",
}
SCENARIO_LABELS = {"clear": "Clear day", "cloud": "Cloud shadow",
                   "wind_drop": "Wind gust drop", "night": "Night operation",
                   "combined": "Combined stress"}

# ================================================================
# 8. WEATHER
# ================================================================
#   "calibrated"  synthetic shapes, levels from data/weather_calibration.json
#   "synthetic"   synthetic shapes, built-in levels
#   "measured"    windows cut from a measured high-resolution record
#                 configured in data/measured/dataset.json (vsg_rl/realdata.py)
WEATHER_SOURCE = "calibrated"
CALIBRATION_FILE = os.path.join(DATA_DIR, "weather_calibration.json")
MEASURED_CONFIG = os.path.join(DATA_DIR, "measured", "dataset.json")
REAL_LAT = 14.9799
REAL_LON = 102.0977

# ================================================================
# 9. PLOT STYLE
# ================================================================
COLORS = {
    "solar": "#F5A623", "wind": "#1E88E5", "bess": "#43A047", "load": "#E53935",
    "none": "#E53935", "fixed_low": "#BDBDBD", "fixed_high": "#757575",
    "fixed_max": "#37474F", "fixed_tuned": "#6D4C41", "adaptive_rule": "#FB8C00",
    "ddpg": "#1976D2", "td3": "#00A86B",
    "rocof": "#FB8C00", "J": "#2E7D32", "D": "#D81B60", "volt": "#8E24AA",
    "limit": "#FF6F00", "dim": "#8A8F99", "text": "#1F2430",
    "q1": "#1976D2", "q2": "#E53935",
}
SCENARIO_COLORS = {"clear": "#F5A623", "cloud": "#1E88E5", "wind_drop": "#00A86B",
                   "night": "#8E24AA", "combined": "#E53935"}
