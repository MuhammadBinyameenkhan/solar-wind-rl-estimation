"""
Convert downloaded NetCDF (.nc) or MATLAB (.mat) files into the simple CSVs
read by `--weather measured` (time,value at 1 s).

Typical use (see docs/REAL_DATA.md):

  # 1. look inside a file to find the variable names
  python tools/convert_to_csv.py inspect cabauw/some_day.nc
  python tools/convert_to_csv.py inspect fino1/some_hour.mat

  # 2. irradiance: Cabauw BSRN 1 Hz NetCDF files -> irradiance.csv
  python tools/convert_to_csv.py irradiance --var <GHI variable> \
      --out data/measured/irradiance.csv cabauw/*.nc

  # 3. wind: FINO1 10 Hz sonic .mat files (80 m) -> wind.csv (1 s means)
  python tools/convert_to_csv.py wind --u u --v v --hz 10 \
      --out data/measured/wind.csv fino1/*80m*.mat

Time is taken, in this order of preference, from a time variable in the file
(CF units "seconds since 2015-01-01 00:00:00" etc.), from a date+time found in
the FILE NAME (e.g. 20070612_1300, 2007061213, 2007-06-12), or, failing both,
files are assumed consecutive in name order.  Only the ORDER of the data
matters to the simulation (chronological train/val/test split), so the last
fallback is safe as long as the file names sort chronologically.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

UNIT_S = {"second": 1.0, "seconds": 1.0, "s": 1.0, "minute": 60.0, "minutes": 60.0,
          "min": 60.0, "hour": 3600.0, "hours": 3600.0, "h": 3600.0,
          "day": 86400.0, "days": 86400.0, "d": 86400.0}


# ----------------------------------------------------------------
# File readers -> {name: (array, attrs)}
# ----------------------------------------------------------------
def _read_h5(path):
    import h5py
    out = {}
    with h5py.File(path, "r") as f:
        def visit(name, obj):
            if isinstance(obj, h5py.Dataset) and obj.dtype.kind in "fiu":
                attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in obj.attrs.items()}
                out[name] = (np.asarray(obj[()], dtype=float).squeeze(), attrs)
        f.visititems(visit)
    return out


def _read_mat(path):
    try:
        from scipy.io import loadmat
        m = loadmat(path, squeeze_me=True, struct_as_record=False)
    except NotImplementedError:          # MATLAB v7.3 = HDF5
        return _read_h5(path)
    out = {}

    def walk(prefix, obj):
        if isinstance(obj, np.ndarray) and obj.dtype.kind in "fiu":
            out[prefix] = (obj.astype(float).squeeze(), {})
        elif hasattr(obj, "_fieldnames"):
            for fn in obj._fieldnames:
                walk(f"{prefix}.{fn}", getattr(obj, fn))
    for k, v in m.items():
        if not k.startswith("__"):
            walk(k, v)
    return out


def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mat":
        return _read_mat(path)
    if ext in (".nc", ".nc4", ".h5", ".hdf5", ".cdf"):
        try:
            return _read_h5(path)            # NetCDF-4 files are HDF5
        except OSError:
            from scipy.io import netcdf_file  # classic NetCDF-3
            out = {}
            with netcdf_file(path, "r", mmap=False) as f:
                for k, v in f.variables.items():
                    if v.data.dtype.kind in "fiu":
                        attrs = {a: (b.decode() if isinstance(b, bytes) else b)
                                 for a, b in v._attributes.items()}
                        out[k] = (np.asarray(v.data, float).squeeze(), attrs)
            return out
    raise ValueError(f"unsupported file type: {path}")


# ----------------------------------------------------------------
# Time
# ----------------------------------------------------------------
def _cf_time(values, units):
    m = re.match(r"\s*(\w+)\s+since\s+(.+)", str(units))
    if not m or m.group(1).lower() not in UNIT_S:
        return None
    base = m.group(2).strip().replace(" ", "T").split("+")[0].rstrip("Z")
    base = re.sub(r"T(\d):", r"T0\1:", base)
    t0 = np.datetime64(base, "ms")
    return t0 + (np.asarray(values) * UNIT_S[m.group(1).lower()] * 1000).astype("timedelta64[ms]")


def _time_from_name(path):
    name = os.path.basename(path)
    for pat, fmt in ((r"(\d{4})(\d{2})(\d{2})[_\-T]?(\d{2})(\d{2})", 5),
                     (r"(\d{4})-(\d{2})-(\d{2})[_\-T ]?(\d{2})[:\-]?(\d{2})", 5),
                     (r"(\d{4})(\d{2})(\d{2})[_\-]?(\d{2})(?!\d)", 4),
                     (r"(\d{4})-(\d{2})-(\d{2})", 3), (r"(\d{4})(\d{2})(\d{2})", 3)):
        m = re.search(pat, name)
        if m:
            g = [int(x) for x in m.groups()] + [0, 0]
            try:
                return np.datetime64(f"{g[0]:04d}-{g[1]:02d}-{g[2]:02d}T{g[3]:02d}:{g[4]:02d}", "ms")
            except ValueError:
                continue
    return None


def _find(vars_, name):
    if name in vars_:
        return name
    low = {k.lower().split(".")[-1].split("/")[-1]: k for k in vars_}
    return low.get(name.lower())


def series_from_file(path, var, hz, time_var=None, v_var=None):
    """-> (datetime64[ms] array or None, values) for one file."""
    vars_ = read_any(path)
    key = _find(vars_, var)
    if key is None:
        raise KeyError(f"{path}: variable '{var}' not found; run 'inspect' to list variables")
    val, _ = vars_[key]
    if v_var:
        kv = _find(vars_, v_var)
        if kv is None:
            raise KeyError(f"{path}: variable '{v_var}' not found")
        val = np.hypot(val, vars_[kv][0])            # horizontal speed
    val = np.atleast_1d(val)

    t = None
    tk = _find(vars_, time_var) if time_var else (_find(vars_, "time") or _find(vars_, "t"))
    if tk is not None and np.size(vars_[tk][0]) == val.size:
        t = _cf_time(vars_[tk][0], vars_[tk][1].get("units", ""))
    if t is None:
        start = _time_from_name(path)
        if start is not None:
            t = start + (np.arange(val.size) * 1000.0 / hz).astype("timedelta64[ms]")
    return t, val


def to_seconds(t, val, hz, out_dt=1.0):
    """Block-average to out_dt (e.g. 10 Hz -> 1 s means)."""
    n = max(1, int(round(out_dt * hz)))
    m = (val.size // n) * n
    v = val[:m].reshape(-1, n)
    good = np.isfinite(v).sum(1) >= 0.8 * n
    vm = np.nanmean(np.where(np.isfinite(v), v, np.nan), axis=1)
    tt = None if t is None else t[:m:n]
    return tt, np.where(good, vm, np.nan)


def convert(files, var, hz, out, time_var=None, v_var=None, clip_min=None, scale=1.0):
    files = sorted(files)
    if not files:
        sys.exit("no input files matched")
    rows_t, rows_v, synthetic_clock = [], [], 0.0
    use_iso = None
    for i, f in enumerate(files):
        t, v = series_from_file(f, var, hz, time_var, v_var)
        t, v = to_seconds(t, v * scale, hz)
        if clip_min is not None:
            v = np.where(v < clip_min, clip_min, v)
        if use_iso is None:
            use_iso = t is not None
            if not use_iso:
                print("  note: no time found in file or name; assuming files are consecutive",
                      file=sys.stderr)
        if use_iso and t is None:
            sys.exit(f"{f}: no time information but earlier files had it")
        if not use_iso:
            t = synthetic_clock + np.arange(v.size, dtype=float)
            synthetic_clock = t[-1] + 1.0
        ok = np.isfinite(v)
        rows_t.append(t[ok]); rows_v.append(v[ok])
        print(f"  [{i + 1}/{len(files)}] {os.path.basename(f)}: {ok.sum()} s", file=sys.stderr)
    T = np.concatenate(rows_t)
    V = np.concatenate(rows_v)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as fh:
        fh.write("time,value\n")
        if use_iso:
            fh.writelines(f"{str(a)[:19]},{b:.4f}\n" for a, b in zip(T, V))
        else:
            fh.writelines(f"{a:.0f},{b:.4f}\n" for a, b in zip(T, V))
    print(f"wrote {out}: {len(V)} rows, {V.min():.2f} .. {V.max():.2f}, "
          f"from {T[0]} to {T[-1]}", file=sys.stderr)


def inspect(path):
    vars_ = read_any(path)
    print(f"{path}: {len(vars_)} numeric variables")
    for k, (a, attrs) in vars_.items():
        a = np.atleast_1d(a)
        fin = a[np.isfinite(a)]
        rng = f"{fin.min():.4g} .. {fin.max():.4g}" if fin.size else "all NaN"
        extra = " ".join(f"{x}={attrs[x]}" for x in ("units", "long_name", "standard_name") if x in attrs)
        print(f"  {k:<40} shape={a.shape!s:<14} {rng:<24} {extra}")
    tn = _time_from_name(path)
    print(f"  time from file name: {tn if tn is not None else 'not recognised'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect"); p.add_argument("file")
    for name in ("irradiance", "wind"):
        p = sub.add_parser(name)
        p.add_argument("files", nargs="+")
        p.add_argument("--out", required=True)
        p.add_argument("--hz", type=float, default=1.0, help="sampling rate of the input")
        p.add_argument("--time-var", default=None)
        p.add_argument("--scale", type=float, default=1.0)
        if name == "irradiance":
            p.add_argument("--var", required=True, help="global horizontal irradiance variable")
        else:
            p.add_argument("--u", required=True, help="first horizontal component (or speed)")
            p.add_argument("--v", default=None, help="second horizontal component (omit if --u is already speed)")
    a = ap.parse_args(argv)
    if a.cmd == "inspect":
        inspect(a.file)
        return
    files = [f for pat in a.files for f in (glob.glob(pat) or [pat])]
    if a.cmd == "irradiance":
        convert(files, a.var, a.hz, a.out, a.time_var, None, clip_min=0.0, scale=a.scale)
    else:
        convert(files, a.u, a.hz, a.out, a.time_var, a.v, clip_min=0.0, scale=a.scale)


if __name__ == "__main__":
    main()
