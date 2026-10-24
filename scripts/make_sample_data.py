"""Write SYNTHETIC ERA5/NASA-POWER-format CSVs to data/sample/ (pipeline testing only)."""
from _common import ROOT, base_parser

from vsgrl.data.synthetic import make_sample_files

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--year", type=int, default=2023)
    a = p.parse_args()
    for f in make_sample_files(ROOT / "data" / "sample", year=a.year):
        print("wrote", f)
