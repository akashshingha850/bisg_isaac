#!/usr/bin/env python3
"""Figures for docs/vio-drift.md: top-down paths (ground truth vs EKF2 vs the raw ZED) of the long-flight drift runs and of the
Kinetix explore flights, EKF2 error against distance flown, and heading error over time. Needs matplotlib (the host's apt one is
broken against numpy 2: use a venv, `python3 -m venv /tmp/p && /tmp/p/bin/pip install matplotlib numpy`).

    /tmp/p/bin/python tests/drift_plot.py --drift $ARCHIVE_DIR/drift --kinetix <dir of <run>.csv> --out docs/figures

`--kinetix` takes CSVs of t,src,x,y,z (src truth = Pegasus state/pose, ekf2 = mavros local_position/pose) exported from each Kinetix
run's rosbag. All paths are displacements from the pre-flight pose, so ground truth, EKF2 and the ZED share one origin.
"""
import argparse
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# The emptied Warehouse's inner walls relative to the take-off point (world x -10.13..9.21, y -12.0..17.8; spawn at (-2.5, 0)).
ROOM = (-7.63, 11.71, -12.0, 17.8)
C_TRUTH, C_EKF, C_ZED = "#222222", "#1f6fd1", "#d1452f"

DRIFT_RUNS = [   # (archive dir name, title)
    ("20261026-vel-only1", "No compass, ZED velocity + yaw\n(control: aborted after 36 m)"),
    ("20261026-compass3", "Compass, ZED position fused\n(aborted in lap 5, 322 m)"),
    ("20261026-compass-vel1", "Compass v2 + ZED velocity\n(landed, 358 m)"),
    ("20261026-compass3-vel1", "Compass v3 + ZED velocity: shipped\n(landed, 359 m)"),
]
KINETIX_RUNS = [
    ("20261026-044419", "Before: no compass, ZED position\nEKF2 max 1.50 m, worst wall 2.41 m"),
    ("20261026-051036", "Before: no compass, ZED position\nEKF2 max 2.73 m, worst wall 4.11 m"),
    ("20261026-041403", "Compass + ZED velocity\nEKF2 max 0.98 m, worst wall 0.66 m"),
    ("20261026-045349", "Compass + ZED velocity\nEKF2 max 0.62 m, worst wall 1.04 m"),
]


def room(ax):
    x0, x1, y0, y1 = ROOM
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="#999999", lw=1.2, ls="--", label="Warehouse walls")
    ax.set_xlim(x0 - 4, x1 + 4)
    ax.set_ylim(y0 - 4, y1 + 4)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_xlabel("x from take-off [m]")


def drift_rows(d):
    rows = [r for r in csv.DictReader(open(os.path.join(d, "samples.csv"))) if r["zed_odom_x"] and r["ekf2_x"]]
    r0 = rows[0]
    out = {"truth": [], "ekf2": [], "zed": [], "dist": [], "eh": [], "zed_eh": [], "t": [], "eyaw": [], "zed_eyaw": []}
    for r in rows:
        out["truth"].append((float(r["tx"]) - float(r0["tx"]), float(r["ty"]) - float(r0["ty"])))
        out["ekf2"].append((float(r["ekf2_x"]) - float(r0["ekf2_x"]), float(r["ekf2_y"]) - float(r0["ekf2_y"])))
        out["zed"].append((float(r["zed_odom_x"]) - float(r0["zed_odom_x"]), float(r["zed_odom_y"]) - float(r0["zed_odom_y"])))
        out["dist"].append(float(r["dist"]))
        out["eh"].append(float(r["ekf2_eh"]))
        out["zed_eh"].append(float(r["zed_odom_eh"]))
        out["t"].append(float(r["t"]) - float(r0["t"]))
        out["eyaw"].append(float(r["ekf2_eyaw"]))
        out["zed_eyaw"].append(float(r["zed_odom_eyaw"]))
    return out


def unwrap(deg):
    out, off = [], 0.0
    for i, v in enumerate(deg):
        if i and v + off - out[-1] > 180:
            off -= 360
        elif i and v + off - out[-1] < -180:
            off += 360
        out.append(v + off)
    return out


def xy(seq):
    return [p[0] for p in seq], [p[1] for p in seq]


def fig_drift_paths(drift, out):
    fig, axs = plt.subplots(1, 4, figsize=(22, 8.5), sharey=True)
    for ax, (name, title) in zip(axs, DRIFT_RUNS):
        d = drift_rows(os.path.join(drift, name))
        room(ax)
        ax.plot(*xy(d["zed"]), color=C_ZED, lw=0.9, alpha=0.75, label="raw ZED (what EKF2 used to follow)")
        ax.plot(*xy(d["truth"]), color=C_TRUTH, lw=1.6, label="ground truth")
        ax.plot(*xy(d["ekf2"]), color=C_EKF, lw=1.2, label="EKF2 (what the drone flew on)")
        ax.plot(*d["truth"][-1], "x", color=C_TRUTH, ms=10, mew=2)
        ax.plot(0, 0, "o", color="#2a9d3f", ms=7)
        ax.set_title(f"{title}\nEKF2 max {max(d['eh']):.2f} m, raw ZED max {max(d['zed_eh']):.1f} m", fontsize=11)
    axs[0].set_ylabel("y from take-off [m]")
    axs[0].legend(loc="lower left", fontsize=9)
    fig.suptitle("Long-flight drift test (5 laps of 12 x 20 m at 2 m, 1 m/s, 360 deg sweep per lap): top view, x = where it ended",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(out, "drift_paths.png"), dpi=110)
    plt.close(fig)


def fig_drift_error(drift, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 5.5))
    colors = ["#888888", "#e39b2d", "#7d4fc4", C_EKF]
    for (name, title), c in zip(DRIFT_RUNS, colors):
        d = drift_rows(os.path.join(drift, name))
        a1.plot(d["dist"], d["eh"], color=c, lw=1.4, label=title.replace("\n", " "))
    best = drift_rows(os.path.join(drift, DRIFT_RUNS[-1][0]))
    a1.plot(best["dist"], best["zed_eh"], color=C_ZED, lw=1, ls="--", label="raw ZED in the shipped run")
    a1.axhline(3.0, color="#cc0000", lw=0.8, ls=":")
    a1.text(5, 3.08, "abort (3 m)", color="#cc0000", fontsize=9)
    a1.set_ylim(0, 6)
    a1.set_xlabel("distance flown [m]")
    a1.set_ylabel("EKF2 horizontal error vs ground truth [m]")
    a1.set_title("Horizontal error against distance flown")
    a1.grid(alpha=0.25)
    a1.legend(fontsize=8.5, loc="upper right")
    a2.plot(best["t"], unwrap(best["zed_eyaw"]), color=C_ZED, lw=1, label="raw ZED heading error")
    a2.plot(best["t"], best["eyaw"], color=C_EKF, lw=1.2, label="EKF2 heading error (compass holding it)")
    a2.axhline(0, color="#999999", lw=0.8)
    a2.set_xlabel("sim time [s]")
    a2.set_ylabel("heading error vs ground truth [deg]")
    a2.set_title("Heading in the shipped run: the ZED slips in turns, the compass pulls EKF2 back")
    a2.grid(alpha=0.25)
    a2.legend(fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "drift_error.png"), dpi=110)
    plt.close(fig)


def kinetix_raw(path):
    tr, ek = [], []
    for r in csv.DictReader(open(path)):
        (tr if r["src"] == "truth" else ek).append((float(r["t"]), float(r["x"]), float(r["y"])))
    t0, e0 = tr[0], min(ek, key=lambda e: abs(e[0] - tr[0][0]))
    return [(t, x - t0[1], y - t0[2]) for t, x, y in tr], [(t, x - e0[1], y - e0[2]) for t, x, y in ek]


def kinetix_rows(path):
    tr, ek = kinetix_raw(path)
    return [(x, y) for _, x, y in tr], [(x, y) for _, x, y in ek]


def kinetix_error(path):
    """(minutes since start, EKF2 horizontal error) at every EKF2 sample, against the latest ground truth sample."""
    tr, ek = kinetix_raw(path)
    j, out = 0, []
    for t, x, y in ek:
        while j < len(tr) - 1 and tr[j + 1][0] <= t:
            j += 1
        out.append(((t - ek[0][0]) / 60.0, math.hypot(x - tr[j][1], y - tr[j][2])))
    return out


def fig_kinetix(kdir, out):
    fig, axs = plt.subplots(1, 4, figsize=(22, 8.5), sharey=True)
    for ax, (name, title) in zip(axs, KINETIX_RUNS):
        tr, ek = kinetix_rows(os.path.join(kdir, name + ".csv"))
        room(ax)
        ax.plot(*xy(tr), color=C_TRUTH, lw=1.6, label="ground truth")
        ax.plot(*xy(ek), color=C_EKF, lw=1.2, label="EKF2 (the pose Kinetix maps and flies on)")
        ax.plot(0, 0, "o", color="#2a9d3f", ms=7)
        ax.set_title(title, fontsize=11, color="#a32020" if name in ("20261026-044419", "20261026-051036") else "#1a6b2f")
    axs[0].set_ylabel("y from take-off [m]")
    axs[0].legend(loc="lower left", fontsize=9)
    fig.suptitle("Kinetix explore in the Warehouse (28 views, ~5 min): top view, ground truth vs EKF2", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(out, "kinetix_explore_paths.png"), dpi=110)
    plt.close(fig)


def fig_kinetix_error(kdir, out):
    fig, ax = plt.subplots(figsize=(11, 5))
    styles = [("#c0392b", "-"), ("#e67e22", "-"), (C_EKF, "-"), ("#16a085", "-")]
    for (name, title), (c, ls) in zip(KINETIX_RUNS, styles):
        e = kinetix_error(os.path.join(kdir, name + ".csv"))
        ax.plot([m for m, _ in e], [v for _, v in e], color=c, ls=ls, lw=1.3, label=title.replace("\n", ": "))
    ax.set_xlabel("wall-clock minutes since the run started (sim runs at ~0.55x)")
    ax.set_ylabel("EKF2 horizontal error vs ground truth [m]")
    ax.set_title("Kinetix explore: EKF2 error over the flight (red/orange before, blue/green with the compass)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "kinetix_explore_error.png"), dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift", required=True, help="archive dir holding the 20261026-* drift runs")
    ap.add_argument("--kinetix", help="dir of <run>.csv path exports")
    ap.add_argument("--out", default="docs/figures")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fig_drift_paths(a.drift, a.out)
    fig_drift_error(a.drift, a.out)
    if a.kinetix:
        fig_kinetix(a.kinetix, a.out)
        fig_kinetix_error(a.kinetix, a.out)
    print("wrote", sorted(f for f in os.listdir(a.out) if f.endswith(".png")))


if __name__ == "__main__":
    main()
