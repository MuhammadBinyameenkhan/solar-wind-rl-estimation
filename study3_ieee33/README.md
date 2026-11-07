# Study 3 — Feasible synthetic inertia on the IEEE 33-bus distribution feeder

Extension of Study 2 (IREA paper, single bus) to a published multi-bus network, addressing the
limitation stated in the IREA paper. Study 2 code and results are not changed by anything here.

## Network data (published, not assumed)
* IEEE 33-bus radial feeder: M. E. Baran and F. F. Wu, "Network reconfiguration in distribution
  systems for loss reduction and load balancing," IEEE Trans. Power Del., 4(2):1401–1407, 1989,
  doi:10.1109/61.25627.
* Transcription used: MATPOWER `case33bw.m`, copied unchanged to `data/source/case33bw_matpower.m`;
  cross-checked against `pandapower.networks.case33bw` (identical line r/x and bus loads).
* 12.66 kV, 33 buses, 32 lines in service, 5 normally open tie lines; 3715 kW / 2300 kVAr.

## Validation of the baseline (`scripts/validate_ieee33_baseline.py`)
| Quantity | Published | Reproduced |
|---|---|---|
| Real power losses | 202.7 kW | 202.68 kW |
| Reactive power losses | 135.1 kVAr | 135.14 kVAr |
| Minimum voltage | 0.9131 pu at bus 18 | 0.9131 pu at bus 18 |

## Status
1. Published network data obtained and verified — done.
2. Design decisions (load scaling, DER placement) — awaiting the author.
3. Multi-bus frequency model, feasibility layer per bus, learning, evaluation — next.
