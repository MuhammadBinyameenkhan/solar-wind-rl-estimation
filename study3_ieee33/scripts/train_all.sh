#!/usr/bin/env bash
# Train TD3 and DDPG (5 seeds each) on the IEEE 33-bus feeder, 2 processes per algorithm.
# Re-running continues interrupted seeds from their last validation checkpoint and skips finished ones.
cd "$(dirname "$0")/../.."
CFG=study3_ieee33/configs/ieee33.yaml
mkdir -p study3_ieee33/results/training
python scripts/train.py --config $CFG --algo td3  --workers 2 >> study3_ieee33/results/training/td3.log 2>&1 &
python scripts/train.py --config $CFG --algo ddpg --workers 2 >> study3_ieee33/results/training/ddpg.log 2>&1 &
wait
