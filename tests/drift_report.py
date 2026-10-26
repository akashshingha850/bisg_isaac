#!/usr/bin/env python3
"""Tables of long-flight drift runs (tests/drift_flight.py output dirs) for docs/vio-drift.md, and a JSON export (stdlib only).

    python3 tests/drift_report.py $ARCHIVE_DIR/drift/20261026-* [--json docs/data/vio_drift_2026-10-26.json]

Per run: landed or aborted (3 m of EKF2 error), distance and sim time flown, EKF2 horizontal error (max / RMS / final), heading error,
and the raw ZED odometry's (what EKF2 followed before the compass), then EKF2's error at each lap end. The config comes from
<dir>/config.json when present ({"heading": ..., "params": {...}}), else from the directory name.
"""
import argparse
import json
import os
import sys


def load(d):
    s = json.load(open(os.path.join(d, "summary.json")))
    cfg_path = os.path.join(d, "config.json")
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    name = os.path.basename(d.rstrip("/"))
    return {"run": name, "config": cfg, "landed": s["landed"], "distance_m": s["distance_m"], "sim_s": s["sim_s"],
            "sources": s["sources"], "laps": s["laps"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args()
    runs = [load(d) for d in a.dirs if os.path.exists(os.path.join(d, "summary.json"))]
    print("| run | heading / EKF2 params | outcome | flown | EKF2 h max / RMS / final | EKF2 yaw final | raw ZED h max | raw ZED yaw final |")
    print("|---|---|---|---|---|---|---|---|")
    for r in runs:
        e, z = r["sources"].get("ekf2", {}), r["sources"].get("zed_odom", {})
        c = r["config"]
        ver = c.get("compass", "").split(":")[0].split(" ")[0]
        cfg = f"{c.get('heading', '?')}{' ' + ver if ver and c.get('heading') == 'manhattan' else ''}; " + (", ".join(f"{k} {v}" for k, v in c.get("params", {}).items()) or "shipped")
        print(f"| {r['run']} | {cfg} | {'landed' if r['landed'] else 'aborted'} | {r['distance_m']:.0f} m, {r['sim_s']:.0f} s | "
              f"{e.get('h_max_m', 0):.2f} / {e.get('h_rms_m', 0):.2f} / {e.get('h_final_m', 0):.2f} m | {e.get('yaw_final_deg', 0):+.1f} deg | "
              f"{z.get('h_max_m', 0):.1f} m | {z.get('yaw_final_deg', 0):+.0f} deg |")
    print("\nEKF2 horizontal error at each lap end (m), distance flown in brackets:\n")
    print("| run | " + " | ".join(f"lap {k}" for k in range(1, 6)) + " |")
    print("|---|" + "---|" * 5)
    for r in runs:
        cells = []
        for k in range(1, 6):
            lap = r["laps"].get(str(k))
            done = lap and str(k + 1) in r["laps"]           # a lap that the abort cut short is not a lap end
            cells.append(f"{lap['ekf2']['h_m']:.2f} ({lap['dist_m']:.0f})" if done and "ekf2" in lap else "-")
        print(f"| {r['run']} | " + " | ".join(cells) + " |")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"about": "tests/drift_flight.py runs, docs/vio-drift.md", "runs": runs}, f, indent=1)
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    sys.exit(main())
