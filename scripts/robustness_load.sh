#!/usr/bin/env bash
# Robustness of the Study 2 conclusions to the load profile (no retraining).
# Three cases: synthetic profile, EGAT peak-scaled (used in the paper), EGAT min-max scaled.
# For each: oracle bound (validation) and the fixed baselines on the 200 test scenarios.
# Outputs: results_robust_<case>/ (per_scenario.csv, scenarios_test.csv) and logs in results_robust_logs/.
set -euo pipefail
CFG=${1:-configs/default.yaml}
LOG=results_robust_logs; mkdir -p "$LOG"
declare -A LOAD=( [synthetic]=null [egat_peak]=data/raw/egat_northeast_2024_load.csv [egat_minmax]=data/raw/egat_northeast_2024_load_minmax.csv )
CASES=(synthetic egat_peak egat_minmax)
set_for() { echo "data.load_csv=${LOAD[$1]} data.processed_csv=data/processed/hourly_resource_$1.csv eval.out_dir=results_robust_$1"; }

for c in "${CASES[@]}"; do   # build each dataset once, before the parallel runs read it
  python scripts/prepare_data.py --config "$CFG" --set $(set_for "$c") > "$LOG/prepare_$c.log" 2>&1
done
for c in "${CASES[@]}"; do
  python scripts/oracle_test.py --config "$CFG" --set $(set_for "$c") > "$LOG/oracle_$c.log" 2>&1 &
  python scripts/evaluate.py --config "$CFG" --controllers fixed_tuned fixed_feasible fixed bang_bang \
         --set $(set_for "$c") > "$LOG/eval_$c.log" 2>&1 &
done
wait
echo "done"
