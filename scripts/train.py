"""Train TD3 / DDPG over several seeds (optionally in parallel processes).

Examples
  python scripts/train.py --algo td3                       # 1000 episodes x 5 seeds (config)
  python scripts/train.py --algo ddpg --seeds 0 1 2 --workers 3
  python scripts/train.py --algo td3 --tag td3_noheadroom --set env.headroom_constraint=false
"""
from concurrent.futures import ProcessPoolExecutor

from _common import base_parser, setup

from vsgrl.data.hybrid import load_processed
from vsgrl.train import run_dir, train_one


def _job(args):
    cfg, algo, seed, out = args
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    return str(train_one(cfg, algo, seed, out))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--algo", choices=["td3", "ddpg"], default=None)
    p.add_argument("--seeds", type=int, nargs="*", default=None)
    p.add_argument("--episodes", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--tag", default=None, help="run name (default: algo) — use for ablations")
    a = p.parse_args()
    cfg = setup(a)
    algo = a.algo or cfg["train"]["algo"]
    if a.episodes:
        cfg["train"]["episodes"] = a.episodes
    seeds = a.seeds if a.seeds is not None else cfg["train"]["seeds"]
    load_processed(cfg)  # build processed dataset once, before forking
    jobs = [(cfg, algo, s, run_dir(cfg, algo, s, a.tag)) for s in seeds]
    if a.workers > 1:
        with ProcessPoolExecutor(a.workers) as ex:
            for d in ex.map(_job, jobs):
                print("done:", d)
    else:
        for j in jobs:
            print("done:", _job(j))
