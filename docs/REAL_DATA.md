# Using measured weather data instead of synthetic profiles

The simulation runs at 20 ms, and inertia emulation acts on a scale of
seconds. A useful dataset therefore needs **≤ 1-second** irradiance and wind.
Hourly or 15-minute data (Open-Meteo, NASA POWER, Thai Meteorological
Department daily totals) can set the *levels* but not the *disturbance shapes*.

The code supports both:

| What | Resolution needed | How it is used |
|---|---|---|
| Disturbance shapes: cloud dips, wind lulls | ≤ 1 s (1-min works but loses sub-minute dynamics) | `--weather measured`: every episode is a real 30 s window cut from the record |
| Site levels for Nakhon Ratchasima | hourly | `data/weather_calibration.json` (`python -m vsg_rl.weather --calibrate`) |

## 0. Recommended combination (both free with a Zenodo/GitHub login)

| | Dataset | Resolution |
|---|---|---|
| Irradiance | **BSRN Cabauw 1 Hz**, part 1: [Zenodo 7093164](https://zenodo.org/records/7093164) (Knap & Mol 2022) | 1 s GHI, 2011–2020 |
| Wind | **FINO1 post-processed sonic anemometer**: [Zenodo 15826678 (2007)](https://zenodo.org/records/15826678), [Zenodo 15826899 (2008)](https://zenodo.org/records/15826899) | 10 Hz, 40/60/**80 m**, hourly `.mat` files, components u, v, w |

FINO1 is a North Sea research platform close to the Netherlands, and its
80 m sonic matches the hub height. The two records are from different years,
which is fine: each scenario window is selected independently, and the
combined scenario is a designed superposition anyway.

Same-site alternative: part 2 of the Cabauw dataset, [Zenodo 7462362](https://zenodo.org/records/7462362),
contains the Cabauw tower wind speed for the same days. It is most likely
10-minute data (check the file), which is too slow for gust dynamics, but it
is useful to cite as site context.

### Quick procedure for Cabauw + FINO1

```bash
pip install -r requirements.txt

# 1  download 1–3 months of Cabauw files and 1–3 months of FINO1 80 m files,
#    unpack them into e.g. downloads/cabauw/ and downloads/fino1/

# 2  look inside one file of each to find the variable names
python tools/convert_to_csv.py inspect downloads/cabauw/<one file>.nc
python tools/convert_to_csv.py inspect downloads/fino1/<one file>.mat

# 3  convert (replace GHI / u / v with the names printed in step 2)
python tools/convert_to_csv.py irradiance --var GHI --hz 1 \
    --out data/measured/irradiance.csv "downloads/cabauw/*.nc"
python tools/convert_to_csv.py wind --u u --v v --hz 10 \
    --out data/measured/wind.csv "downloads/fino1/*.mat"

# 4  configure (the example is already set up for these two CSVs; height_m = 80)
cp data/measured/dataset.example.json data/measured/dataset.json

# 5  check, then run
python -m vsg_rl.realdata --check
python -m vsg_rl --weather measured --smoke
python -m vsg_rl --weather measured --out results_measured --fresh
```

If the FINO1 files contain only the along-wind component, use `--u u` and
omit `--v`. If a FINO1 folder mixes 40, 60 and 80 m files, convert only the
80 m ones (for example `"downloads/fino1/*80*.mat"`).

## 1. Where to get the data (all options)

### Irradiance (choose one)

| Dataset | Resolution | Notes |
|---|---|---|
| **NREL Oahu Solar Measurement Grid** — [data.nrel.gov/submissions/11](https://data.nrel.gov/submissions/11), mirror [OpenEI](https://data.openei.org/submissions/6264) | **1 s**, 17 stations, ~1 year | **Recommended.** Tropical trade-wind cumulus, the closest public match to Thai conditions. Free. |
| BSRN Cabauw 1 Hz — [Zenodo 7093164](https://zenodo.org/records/7093164) | 1 s, 10 years | Mid-latitude (Netherlands) climate. |
| BSRN network — [bsrn.awi.de/data](https://bsrn.awi.de/data) | 1 min | Many stations; free registration. Too slow for sub-minute cloud edges. |
| Thai ground stations (DEDE / Silpakorn University: Chiang Mai, Ubon Ratchathani, Nakhon Pathom, Songkhla; Thai Meteorological Department) | 1 min at some stations | Not openly downloadable; request from DEDE or Silpakorn University. Best for a Thai paper if you can obtain it. |
| **Your own SUT measurements** (a pyranometer or PV-plant logger on campus) | whatever is logged | Strongest option: it is the actual site. |

### Wind (choose one)

| Dataset | Resolution | Notes |
|---|---|---|
| **NREL NWTC M4/M5 135 m met masts** — [wind.nrel.gov/MetData](https://wind.nrel.gov/MetData) ([M5](https://wind.nrel.gov/MetData/M5Twr)) | **20 Hz sonic, 1 Hz cups**, several heights including ~80 m | **Recommended.** Free; average to 1 s. Processing code: [NREL/MetMastVis](https://github.com/NREL/MetMastVis). |
| NREL NWTC M2 tower — [MIDC](https://midcdmz.nrel.gov/apps/go2url.pl?site=NWTC) | 1-min averages | Easy to download, but too coarse for gust dynamics. |
| SUT or a nearby Thai wind project's met mast | — | Best if available; ask the operator for 1 s or 10 s SCADA data. |

### Site levels (already supported)

[Open-Meteo historical weather API](https://open-meteo.com/en/docs/historical-weather-api)
(ERA5 reanalysis, hourly, free, no key) gives Nakhon Ratchasima's levels.

## 2. Step-by-step procedure

### Step 1 — Download

* **Irradiance:** from the Oahu archive download **one station** (any of the
  17) for **2–4 weeks**. That gives enough cloud events for the
  train / validation / test splits (the code needs about 40 candidate events per
  split, at least 30 s apart).
* **Wind:** from NWTC M5 (or M4) download **2–4 weeks** of the horizontal
  wind speed nearest 80 m height.

### Step 2 — Convert each file to a simple CSV

Each file needs a header row, a time column and a value column. Any column
names work; you name them in the config in Step 3. Time can be ISO
(`2010-07-01 06:30:01`) or numeric seconds. If the downloaded files have a
different layout (separate date/time columns, several stations per file), a
few lines of pandas convert them:

```python
import pandas as pd

# Irradiance -- adapt the column names to the downloaded file
df = pd.read_csv("downloaded_oahu_file.csv")
df["time"] = pd.to_datetime(df["<date column>"] + " " + df["<time column>"])
df[["time", "<GHI column of your station>"]].rename(
    columns={"<GHI column of your station>": "ghi"}).to_csv(
    "data/measured/irradiance.csv", index=False)

# Wind -- average 20 Hz to 1 s
w = pd.read_csv("downloaded_m5_file.csv")
w["time"] = pd.to_datetime(w["<timestamp column>"])
w = w.set_index("time")["<wind speed column at ~80 m>"].resample("1s").mean().dropna()
w.rename("wind_speed").to_csv("data/measured/wind.csv")
```

### Step 3 — Point the code at the files

```bash
cp data/measured/dataset.example.json data/measured/dataset.json
```

Edit `data/measured/dataset.json`:

* `irradiance.file`, `time_column`, `value_column`
* `wind.file`, `time_column`, `value_column`, and **`height_m`**, the
  anemometer height. The code corrects it to the 80 m hub with a power law.
* `rescale_to_site` (default `true`):
  * `true` keeps each window's **measured relative variability** but sets its
    pre-event level to the Nakhon Ratchasima levels in
    `data/weather_calibration.json`. Use this when the data come from another
    site (Oahu, Colorado).
  * `false` uses the raw levels. Choose this with Thai/SUT data.
* `split_fractions` (default 70 / 15 / 15 % of the record **by time**) sets the
  train / validation / test segments, so the agents are tested on weather
  they never trained on.

### Step 4 — (Optional) refresh the site levels

On a machine with internet:

```bash
python -m vsg_rl.weather --calibrate --start 2024-01-01 --end 2024-12-31
```

### Step 5 — Check what was detected

```bash
python -m vsg_rl.realdata --check
```

This prints the number of cloud, clear, night and wind-drop windows found in
each split and saves `results/measured_preview.png` with the five test
scenarios. Look at the picture: the cloud window should show a real
irradiance dip, and the wind-drop window a real fall.

If a split has zero windows for a scenario, download a longer period. If
there are no night windows, night is simulated with zero irradiance, which is
exact.

### Step 6 — Smoke test, then the full study

```bash
python -m vsg_rl --weather measured --smoke                         # ~1-2 min
python -m vsg_rl --weather measured --out results_measured --fresh  # ~4 h on 4 cores
```

Results land in `results_measured/` in exactly the same format as before
(`RESULTS.md`, tables, figures).

## 3. How the scenarios are built from the record

| Scenario | Irradiance window | Wind window |
|---|---|---|
| Clear day | steadiest high-irradiance 30 s | any 30 s with wind > 3 m/s |
| Cloud shadow | deepest 5 s relative drop (irradiance > half its daytime P90) | any |
| Wind gust drop | steadiest irradiance | largest 10 s wind fall (starting above 4 m/s) |
| Night | irradiance < 5 W/m² throughout | any |
| Combined stress | the cloud window | the wind-drop window, played **simultaneously** |

Each event starts 20 % into its window, as in the synthetic scenarios. The
deterministic **test** uses the strongest event of the test segment. Training
and the stress test sample among the 40 strongest events of their own
segments. The load contingencies are unchanged: they remain a designed
grid-code test, not weather.

## 4. What to write in the paper

> *Disturbance profiles are taken from measured 1-s data: global horizontal
> irradiance from the NREL Oahu Solar Measurement Grid [ref] (station …,
> dates …) and hub-height wind speed from the NREL NWTC M5 met mast [ref]
> (… m, 20 Hz averaged to 1 s, dates …). Each 30-s episode is a window of
> these records, selected automatically by event type (Section 3.5). The
> record is split chronologically into training (70 %), validation (15 %)
> and test (15 %) segments. Because no public 1-s record exists for Nakhon
> Ratchasima, the windows retain their measured relative variability and are
> rescaled to the site's steady-state levels obtained from ERA5 reanalysis
> [ref]. The combined-stress scenario superimposes a measured cloud event
> and a measured wind lull to represent a worst case.*

Cite the dataset DOIs given on the download pages, e.g. the Oahu grid's
DOI 10.7799/1052451.
