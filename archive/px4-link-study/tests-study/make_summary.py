#!/usr/bin/env python3
"""Cross-dataset summary table (stdlib): median over datasets of the flight ATE / landing-start error / local accuracy.
    python3 tests/study/make_summary.py logs/study/d1 logs/study/d2 [logs/study/d4]
"""
import csv
import statistics as st
import sys

runs = [p.rstrip("/") for p in sys.argv[1:]]
data = {}
for r in runs:
    for row in csv.DictReader(open(r + "/analysis/configs.csv")):
        data.setdefault(row["config"], {})[r.split("/")[-1]] = row
names = [r.split("/")[-1] for r in runs]
cfgs = [c for c in data if all(n in data[c] for n in names) and data[c][names[0]].get("ate_flight")]
cfgs.sort(key=lambda c: st.mean(float(data[c][n]["ate_flight"]) for n in names))
print("| config | " + " | ".join(f"ATE flight {n} [m]" for n in names) + " | mean | err at landing start (mean) [m] | RPE 1 s (mean) [m/m] | rot RPE (mean) [deg/s] | jumps (sum) |")
print("|---|" + "---|" * (len(names) + 5))
for c in cfgs:
    a = [float(data[c][n]["ate_flight"]) for n in names]
    e = st.mean(float(data[c][n]["err_at_land"]) for n in names)
    rpe = st.mean(float(data[c][n]["rpe_1s"]) for n in names)
    rot = st.mean(float(data[c][n]["rot_rpe_1s"]) for n in names)
    j = sum(float(data[c][n]["jumps"]) for n in names)
    print(f"| {c} | " + " | ".join(f"{x:.2f}" for x in a) + f" | **{st.mean(a):.2f}** | {e:.2f} | {rpe:.3f} | {rot:.1f} | {j:.0f} |")
