#!/usr/bin/env python3
"""Merge every bench JSON (+ resources JSON) in logs/perception/ into one Markdown comparison, per scenario tag.

    perception_report.py [LOGDIR]

Columns: ros2 (CPU) | isaac_ros (GPU) | isaac_ros + IMU (tag <scenario>_imu). Repeated runs are aggregated as
`mean (min-max)`; a single run prints the value alone. Run n is shown in the header row.
"""
import glob
import json
import os
import sys


def runs(d, backend, tag):
    out = []
    for f in sorted(glob.glob(os.path.join(d, f"{backend}_{tag}_2*.json"))):
        if "resources" in f:
            continue
        r = f[:-5] + ".resources.json"
        # resources file is stamped by the host a moment earlier than the bench file: take the nearest one before it
        cands = sorted(g for g in glob.glob(os.path.join(d, f"{backend}_{tag}_*.resources.json")) if os.path.getmtime(g) <= os.path.getmtime(f) + 120)
        out.append((json.load(open(f)), json.load(open(cands[-1])) if cands else None))
    return out


def agg(vals, nd=2, unit="", scale=1.0):
    v = [x * scale for x in vals if x is not None and x == x]
    if not v:
        return "–"
    m = sum(v) / len(v)
    return f"{m:.{nd}f}{unit}" if len(v) == 1 else f"{m:.{nd}f}{unit} ({min(v):.{nd}f}–{max(v):.{nd}f})"


def res(r, prefix, suffix, field="mean"):
    if not r:
        return None
    k = next((k for k in r if k.startswith(prefix) and k.endswith(suffix)), None)
    return r[k][field] if k else None


def main():
    d = next((a for a in sys.argv[1:] if not a.startswith("--")), "logs/perception")
    tags = sorted({os.path.basename(f).split("_", 1)[1].rsplit("_", 2)[0].removesuffix("_imu") for f in glob.glob(os.path.join(d, "*_*_2*.json"))
                   if "resources" not in f})
    for t in tags:
        cols = {n: runs(d, b, tt) for n, b, tt in (("ros2 (CPU)", "ros2", t), ("isaac_ros (GPU)", "isaac_ros", t), ("isaac_ros + IMU", "isaac_ros", t + "_imu"))}
        cols = {n: v for n, v in cols.items() if v}
        if not cols:
            continue
        names = list(cols)
        print(f"\n### {t}\n\n| Metric | " + " | ".join(names) + " |\n|---|" + "---:|" * len(names))

        def row(label, fn):
            print(f"| {label} | " + " | ".join(fn(cols[n]) for n in names) + " |")

        def hdr(label):
            print(f"| **{label}** | " + " | ".join("" for _ in names) + " |")
        o = lambda k: (lambda rs: [b["odometry"].get(k) for b, _ in rs])  # noqa: E731
        dp = lambda k: (lambda rs: [b["depth"].get(k) for b, _ in rs])    # noqa: E731
        row("runs", lambda rs: str(len(rs)))
        row("sim real-time factor", lambda rs: agg([b.get("rtf") for b, _ in rs], 2, "×"))
        hdr("Odometry (vs sim ground truth)")
        row("output rate (sim Hz)", lambda rs: agg(o("rate_hz_sim")(rs), 1))
        row("ATE RMSE, rigid-aligned (m)", lambda rs: agg(o("ate_rmse_m")(rs), 2))
        row("ATE RMSE, origin-aligned (m)", lambda rs: agg(o("origin_rmse_m")(rs), 2))
        row("max error, origin-aligned (m)", lambda rs: agg(o("origin_max_m")(rs), 2))
        row("end-point drift over an 18 m path (m)", lambda rs: agg(o("end_drift_m")(rs), 2))
        row("scale (1 = metric)", lambda rs: agg(o("scale")(rs), 2))
        row("latency p50 (wall ms)", lambda rs: agg(o("lat_wall_ms_p50")(rs), 1))
        row("latency p95 (wall ms)", lambda rs: agg(o("lat_wall_ms_p95")(rs), 1))
        hdr("Stereo depth (vs sim depth, 0.5–6 m)")
        row("output rate (sim Hz)", lambda rs: agg(dp("rate_hz_sim")(rs), 1))
        row("coverage of sim-valid pixels", lambda rs: agg(dp("coverage")(rs), 0, " %", 100))
        row("median |error| (m)", lambda rs: agg(dp("medae")(rs), 2))
        row("median relative error", lambda rs: agg(dp("rel")(rs), 0, " %", 100))
        for rng in ("0.5-1.5", "1.5-3.0", "3.0-6.0"):
            g = lambda k, rng=rng: (lambda rs: [b["depth"].get("by_range_m", {}).get(rng, {}).get(k) for b, _ in rs])  # noqa: E731
            row(f"{rng} m: coverage / bias est÷gt", lambda rs, g=g: f"{agg(g('cov')(rs), 0, ' %', 100)} / {agg(g('bias_ratio')(rs), 2)}")
        row("latency p50 / p95 (wall ms)", lambda rs: f"{agg(dp('lat_wall_ms_p50')(rs), 1)} / {agg(dp('lat_wall_ms_p95')(rs), 1)}")
        hdr("Resources (backend container)")
        row("CPU % mean (100 = 1 core)", lambda rs: agg([res(r, "bisg-perception", "cpu_pct") for _, r in rs], 0))
        row("RAM (MiB)", lambda rs: agg([res(r, "bisg-perception", "mem_mib") for _, r in rs], 0))
        row("GPU memory held (MiB)", lambda rs: agg([res(r, "perception_gpu", "mem_mib", "max") if r else None for _, r in rs], 0))
        row("whole-GPU utilisation % (sim + backend)", lambda rs: agg([res(r, "gpu_util", "gpu_util") for _, r in rs], 0))
        row("CPU time per depth frame (ms)", lambda rs: agg([(res(r, "bisg-perception", "cpu_pct") / 100 / b["depth"]["rate_hz_wall"] * 1000)
                                                             if r and b["depth"].get("rate_hz_wall") else None for b, r in rs], 0))


if __name__ == "__main__":
    main()
