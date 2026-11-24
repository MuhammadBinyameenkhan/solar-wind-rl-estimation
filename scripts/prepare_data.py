"""Build the processed hybrid hourly dataset (ERA5 wind + NASA POWER solar) and print a summary."""
from _common import base_parser, setup

from vsgrl.config import resolve_path
from vsgrl.data.hybrid import build_hybrid_dataset, summarize

if __name__ == "__main__":
    a = base_parser(__doc__).parse_args()
    cfg = setup(a)
    df = build_hybrid_dataset(cfg)
    out = resolve_path(cfg["data"]["processed_csv"])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    summ = summarize(df, cfg)
    summ.to_csv(out.with_name(out.stem + "_summary.csv"), index=False)
    print(summ.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("wrote", out)
