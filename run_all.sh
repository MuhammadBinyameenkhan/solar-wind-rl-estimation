#!/usr/bin/env bash
# Full study: data → oracle check → baseline tuning → training (TD3 + DDPG, all seeds)
# → evaluation → statistics → Pareto → figures → MATLAB export.
# Usage: bash run_all.sh [config] [workers]
set -euo pipefail
CFG=${1:-configs/default.yaml}
W=${2:-4}
python scripts/prepare_data.py   --config "$CFG"
python scripts/oracle_test.py    --config "$CFG"     # go/no-go: how much can adaptation gain at most?
python scripts/tune_baselines.py --config "$CFG"     # paste the printed gains into the config if they changed
python scripts/train.py --config "$CFG" --algo td3  --workers "$W"
python scripts/train.py --config "$CFG" --algo ddpg --workers "$W"
python scripts/evaluate.py --config "$CFG"
python scripts/analyze.py  --config "$CFG"
python scripts/pareto.py   --config "$CFG"
python scripts/plot.py     --config "$CFG"
python scripts/export_matlab.py --config "$CFG"
