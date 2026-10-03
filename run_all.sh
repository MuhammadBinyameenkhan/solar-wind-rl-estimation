#!/usr/bin/env bash
# Full study: data → training (TD3 + DDPG, all seeds) → evaluation → statistics → figures → MATLAB export.
# Usage: bash run_all.sh [config] [workers]
set -euo pipefail
CFG=${1:-configs/default.yaml}
W=${2:-5}
python scripts/prepare_data.py --config "$CFG"
python scripts/train.py --config "$CFG" --algo td3  --workers "$W"
python scripts/train.py --config "$CFG" --algo ddpg --workers "$W"
python scripts/evaluate.py --config "$CFG"
python scripts/analyze.py  --config "$CFG"
python scripts/plot.py     --config "$CFG"
python scripts/export_matlab.py --config "$CFG"
