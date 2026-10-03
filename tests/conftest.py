import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vsgrl.config import load_config  # noqa: E402
from vsgrl.data.synthetic import make_sample_files  # noqa: E402


@pytest.fixture(scope="session")
def cfg(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    era5, nasa = make_sample_files(d, year=2023)
    return load_config("configs/default.yaml", [
        f"data.era5_csv={era5}", f"data.nasa_power_csv={nasa}",
        f"data.processed_csv={d / 'processed.csv'}",
        "train.warmup_steps=50", "train.batch_size=32", "train.hidden=[32,32]",
    ])


@pytest.fixture(scope="session")
def df(cfg):
    from vsgrl.data.hybrid import load_processed
    return load_processed(cfg)
