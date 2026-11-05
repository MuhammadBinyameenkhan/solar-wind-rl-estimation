#!/usr/bin/env bash
# Full Study 2 re-run after a change of input data (here: measured EGAT load profile).
# Run AFTER prepare_data.py, oracle_test.py and tune_baselines.py, and after the tuned gains
# printed by tune_baselines.py have been written into eval.baseline_params of the config.
# Usage: bash scripts/rerun_study2.sh [config] [workers]
set -euo pipefail
CFG=${1:-configs/default.yaml}
W=${2:-4}
log() { echo "[$(date '+%F %T')] $*"; }

log "training TD3 (5 seeds)";                       python scripts/train.py --config "$CFG" --algo td3  --workers "$W"
log "training DDPG (5 seeds)";                      python scripts/train.py --config "$CFG" --algo ddpg --workers "$W"
log "training TD3 without projection (5 seeds)";    python scripts/train.py --config "$CFG" --algo td3 --tag td3_noproj --workers "$W" --set env.headroom_constraint=false

log "evaluation: baselines + validation-selected"; python scripts/evaluate.py --config "$CFG"
log "evaluation: TD3 without projection (best)";   python scripts/evaluate.py --config "$CFG" --controllers td3_noproj
log "evaluation: final checkpoints";               python scripts/evaluate.py --config "$CFG" --checkpoint final --controllers td3 ddpg td3_noproj

log "statistics";                                  python scripts/analyze.py --config "$CFG" --reference td3_final
log "Pareto / dominance";                          python scripts/pareto.py  --config "$CFG"
log "feasibility-rule ablation";                   python scripts/headroom_ablation.py --config "$CFG" --n 200 --workers "$W"
log "figures";                                     python scripts/plot.py --config "$CFG"; python scripts/plot_headroom_ablation.py --config "$CFG"
log "MATLAB export";                               python scripts/export_matlab.py --config "$CFG"
log "done"
