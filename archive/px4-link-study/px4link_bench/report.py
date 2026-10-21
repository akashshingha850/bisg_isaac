#!/usr/bin/env python3
"""Turn logs/px4link_bench/<run>/results.json into the markdown tables of docs/study-px4-link.md.

    python3 tools/px4link_bench/report.py logs/px4link_bench/run1 [more run dirs ...]   > tables.md
"""
import json
import os
import statistics as st
import sys

LABEL = {"mavros": "MAVROS (default plugins)", "mavros_lean": "MAVROS (lean plugin list)", "mavsdk": "MAVSDK 4.x (native)", "mavsdk_grpc": "MAVSDK (gRPC)", "dds": "uXRCE-DDS"}
ORDER = ["mavros", "mavros_lean", "mavsdk", "mavsdk_grpc", "dds"]


def load(dirs):
    """Later run directories override earlier ones for every (method, phase) they contain (re-runs after a harness fix)."""
    rows = []
    for d in dirs:
        new = json.load(open(os.path.join(d, "results.json")))
        keys = {(r.get("method"), r.get("phase")) for r in new}
        rows = [r for r in rows if (r.get("method"), r.get("phase")) not in keys] + new
    return rows


def pick(rows, method, phase):
    return [r for r in rows if r.get("method") == method and r.get("phase") == phase and "error" not in r]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.fmean(xs) if xs else None


def get(r, *path):
    for p in path:
        if r is None:
            return None
        r = r.get(p) if isinstance(r, dict) else None
    return r


def avg(rs, *path):
    return mean([get(r, *path) for r in rs])


def f(x, nd=1, unit=""):
    return "n/a" if x is None else f"{x:.{nd}f}{unit}"


def total_cpu(r):
    b, c = get(r, "resources", "bridge_cpu_pct_mean"), get(r, "resources", "client_cpu_pct_mean")
    return None if b is None or c is None else b + c


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main():
    rows = load(sys.argv[1:])
    ms = [m for m in ORDER if any(r.get("method") == m for r in rows)]
    errs = [r for r in rows if "error" in r]
    out = []

    out.append("### Connect, idle footprint (bridge running, nothing flowing; 6 s warm-up excluded)\n")
    t = []
    for m in ms:
        idle = pick(rows, m, "idle")
        t.append([LABEL[m], f(avg(idle, "connect_s"), 1, " s"), f(avg(idle, "startup_cpu_s"), 1, " s"),
                  f(avg(idle, "resources", "bridge_cpu_pct_mean"), 1, " %"), f(avg(idle, "resources", "bridge_rss_mb"), 0, " MB"),
                  f(avg(idle, "resources", "client_cpu_pct_mean"), 1, " %"), f(avg(idle, "resources", "client_rss_mb"), 0, " MB")])
    out.append(table(["method", "connect", "CPU spent connecting", "bridge CPU (idle)", "bridge RSS", "client CPU", "client RSS"], t))

    out.append("\n### Telemetry in (PX4 -> companion), default stream settings, 20 s\n")
    t = []
    for m in ms:
        tel = pick(rows, m, "telemetry")
        c = lambda k, p: avg(tel, "streams", k, p)  # noqa: E731
        t.append([LABEL[m], f(c("attitude", "hz"), 0, " Hz"), f(c("attitude", "gap_p95_ms"), 1, " ms"), f(c("attitude", "gap_max_ms"), 1, " ms"),
                  f(c("position", "hz"), 0, " Hz"), f(c("position", "gap_p95_ms"), 1, " ms"),
                  f(avg(tel, "resources", "bridge_cpu_pct_mean"), 1, " %"), f(avg(tel, "resources", "client_cpu_pct_mean"), 1, " %"),
                  f(avg(tel, "px4", "bandwidth", "mavlink_tx_Bps"), 0) if m != "dds" else f(avg(tel, "px4", "bandwidth", "dds_tx_Bps"), 0)])
    out.append(table(["method", "attitude rate", "attitude gap p95", "attitude gap max", "position rate", "position gap p95",
                      "bridge CPU", "client CPU", "PX4 tx B/s on that link"], t))

    out.append("\n### Command -> ACK round trip (200 x set HOLD mode; PX4 SIH on the same host)\n")
    t = []
    for m in ms:
        r = pick(rows, m, "rtt")
        g = lambda k: avg(r, "rtt_ms", k)  # noqa: E731
        t.append([LABEL[m], f(g("p50"), 1, " ms"), f(g("p95"), 1, " ms"), f(g("p99"), 1, " ms"), f(g("max"), 1, " ms"),
                  f(avg(r, "resources", "bridge_cpu_pct_mean"), 1, " %")])
    out.append(table(["method", "p50", "p95", "p99", "max", "bridge CPU"], t))

    out.append("\n### External-vision odometry, 30 Hz for 20 s: what PX4 received (pose sent: ENU/FLU like a ROS/ZED user has it)\n")
    t = []
    for m in ms:
        r = pick(rows, m, "odom")
        ok = [x for x in r if get(x, "px4", "odometry", "topic")]
        t.append([LABEL[m], get(ok[0], "px4", "odometry", "topic") if ok else "none received",
                  f(avg(r, "px4", "rates", "vehicle_visual_odometry") or avg(r, "px4", "rates", "vehicle_mocap_odometry"), 1, " Hz"),
                  f(avg(ok, "px4", "odometry", "pos_err_m"), 5, " m"), f(avg(ok, "px4", "odometry", "att_err_deg"), 4, "°"),
                  f(avg(ok, "px4", "odometry", "vel_err"), 5), f(avg(ok, "px4", "odometry", "angvel_err"), 5),
                  f(avg(r, "resources", "bridge_cpu_pct_mean"), 1, " %"), f(avg(r, "resources", "client_cpu_pct_mean"), 1, " %"),
                  f(avg(ok, "px4", "bandwidth", "mavlink_rx_Bps") if m != "dds" else avg(ok, "px4", "bandwidth", "dds_rx_Bps"), 0)])
    out.append(table(["method", "PX4 topic", "rate seen by PX4", "position err", "attitude err", "velocity err", "ang-vel err",
                      "bridge CPU", "client CPU", "PX4 rx B/s"], t))

    out.append("\n### Offboard position setpoints: rate PX4 actually registers vs rate sent (armed + OFFBOARD, 16 s)\n")
    t = []
    for m in ms:
        row = [LABEL[m]]
        for rate in (50, 100, 200):
            r = pick(rows, m, f"offboard{rate}")
            if not r:
                row.append("n/a")
                continue
            reg = avg(r, "px4", "rates", "offboard_control_mode")
            row.append(f"{f(reg, 0)} / {f(avg(r, 'sent_hz'), 0)} Hz ({get(r[0], 'px4', 'nav_state')}), bridge {f(avg(r, 'resources', 'bridge_cpu_pct_mean'), 0)} % + client {f(avg(r, 'resources', 'client_cpu_pct_mean'), 0)} %")
        t.append(row)
    out.append(table(["method", "target 50 Hz: PX4 / sent", "target 100 Hz", "target 200 Hz"], t))

    out.append("\n### Under CPU contention: client + bridge pinned to 2 cores that two busy loops also occupy (all other numbers are unloaded)\n")
    t = []
    for m in ms:
        r, tl = pick(rows, m, "rtt_load"), pick(rows, m, "telemetry_load")
        g = lambda k: avg(r, "rtt_ms", k)  # noqa: E731
        t.append([LABEL[m], f(g("p50"), 1, " ms"), f(g("p95"), 1, " ms"), f(g("max"), 0, " ms"),
                  f(avg(tl, "streams", "attitude", "gap_p95_ms"), 1, " ms"), f(avg(tl, "streams", "attitude", "gap_max_ms"), 0, " ms"),
                  f(avg(tl, "streams", "attitude", "hz"), 0, " Hz")])
    out.append(table(["method", "command RTT p50", "p95", "max", "attitude gap p95", "attitude gap max", "attitude rate"], t))

    if errs:
        out.append("\n### Runs that failed\n")
        out += [f"- {e.get('method')} {e.get('phase')}: `{str(e.get('error'))[:160]}`" for e in errs]
    print("\n".join(out))


if __name__ == "__main__":
    main()
