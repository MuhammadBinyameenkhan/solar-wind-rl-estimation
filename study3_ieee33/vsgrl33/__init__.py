"""Study 3: the Study 2 framework on the published IEEE 33-bus feeder."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]       # repository root, for the Study 2 package vsgrl
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
