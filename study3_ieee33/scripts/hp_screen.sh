#!/usr/bin/env bash
# Option C: equal hyperparameter screen for TD3 and DDPG on the IEEE 33-bus plant.
# The same 4 settings, the same 2 seeds and the same 500-episode budget for both algorithms; the
# setting is chosen per algorithm by the mean best VALIDATION return over the seeds
# (study3_ieee33/scripts/hp_select.py). The test set is not used. Resumable: re-run after an
# interruption and finished runs are skipped, interrupted ones resume from resume.pt.
#   h0  current setting           actor 1e-4, critic 3e-4, exploration noise 0.10
#   h1  TD3 author defaults       actor 3e-4, critic 3e-4 (Fujimoto et al., ICML 2018, reference code)
#   h2  DDPG paper                actor 1e-4, critic 1e-3 (Lillicrap et al., ICLR 2016)
#   h3  current, more exploration actor 1e-4, critic 3e-4, exploration noise 0.20
cd "$(dirname "$0")/../.."
CFG=study3_ieee33/configs/ieee33.yaml
OUT=study3_ieee33/runs_hp
mkdir -p study3_ieee33/results/hp_screen
declare -A HP=(
  [h0]="train.actor_lr=1.0e-4 train.critic_lr=3.0e-4 train.expl_noise=0.10"
  [h1]="train.actor_lr=3.0e-4 train.critic_lr=3.0e-4 train.expl_noise=0.10"
  [h2]="train.actor_lr=1.0e-4 train.critic_lr=1.0e-3 train.expl_noise=0.10"
  [h3]="train.actor_lr=1.0e-4 train.critic_lr=3.0e-4 train.expl_noise=0.20"
)
for h in h0 h1 h2 h3; do
  for algo in td3 ddpg; do
    python scripts/train.py --config $CFG --algo $algo --tag ${algo}_$h --seeds 0 1 --episodes 500 --workers 2 \
      --set train.out_dir=$OUT ${HP[$h]} >> study3_ieee33/results/hp_screen/${algo}_$h.log 2>&1 &
  done
  wait
done
