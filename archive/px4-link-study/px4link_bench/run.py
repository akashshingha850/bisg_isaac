#!/usr/bin/env python3
"""
Host-side orchestrator of the PX4 <-> Jetson link benchmark (docs/study-px4-link.md).

For every (method, phase) it restarts a standalone PX4 SITL (SIH physics, tools/px4link_bench/px4.sh), runs bench.py in the
companion container, and in parallel reads the PX4 side (uORB rates, the external-vision message PX4 actually received, link
bandwidth). Writes logs/px4link_bench/<stamp>/results.json and results.md.

    python3 tools/px4link_bench/run.py                      # everything, 2 repeats
    python3 tools/px4link_bench/run.py --methods dds mavros --phases rtt odom --repeats 1
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COMPANION = "bisg-px4link"
ENV = ("export PYTHONDONTWRITEBYTECODE=1 ROS_DOMAIN_ID=77; source /opt/ros/jazzy/setup.bash; source /opt/px4_ws/install/setup.bash; "
       "cd /workspace/tools/px4link_bench")
METHODS = ["mavros", "mavros_lean", "mavsdk", "mavsdk_grpc", "dds"]
PHASES = {"idle": dict(seconds=20), "telemetry": dict(seconds=20), "rtt": dict(n=200), "odom": dict(seconds=20, rate=30),
          "offboard50": dict(seconds=16, rate=50), "offboard100": dict(seconds=16, rate=100), "offboard200": dict(seconds=16, rate=200),
          "telemetry_load": dict(seconds=20), "rtt_load": dict(n=200)}   # *_load: pinned to cores 22-23, which two busy loops also occupy


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw).stdout


def px4_up():
    subprocess.run([os.path.join(HERE, "px4.sh"), "up"], check=True)


def px4(cmd):
    return sh(f"{HERE}/px4.sh cmd {cmd}")


def mavlink_status_block():
    """`mavlink status` prints to the PX4 daemon's stdout (sometimes also back to the client): read the newest dump from the
    container log, retrying until one newer than the request shows up."""
    marker = "\ninstance #0:"
    before = sh("docker logs bisg-px4-sih 2>&1").count(marker)
    for _ in range(4):
        px4("mavlink status")
        time.sleep(1.0)
        log = sh("docker logs --tail 700 bisg-px4-sih 2>&1")
        if sh("docker logs bisg-px4-sih 2>&1").count(marker) > before and marker in log:
            return log[log.rindex(marker):]
    return ""


def px4_bandwidth():
    """B/s of the two links the benchmark uses: the MAVLink onboard instance (UDP 14580) and the uXRCE-DDS client."""
    log = mavlink_status_block()
    out = {}
    for block in re.split(r"\ninstance #", log):
        if "UDP (14581" in block:
            tx = re.search(r"\n\s+tx: ([\d.]+) B/s", block)
            rx = re.search(r"\n\s+rx: ([\d.]+) B/s", block)
            out["mavlink_tx_Bps"] = float(tx.group(1)) if tx else None
            out["mavlink_rx_Bps"] = float(rx.group(1)) if rx else None
            # per-message receive rates PX4 itself counts (msgid -> Hz): the direct "how many did PX4 get" measure
            out["mavlink_rx_msgs"] = {int(i): float(h) for i, h in re.findall(r"msgid:\s+(\d+), Rate:\s+([\d.]+) Hz", block.split("Received Messages:")[-1])
                                      if float(h) > 0}
    dds = px4("uxrce_dds_client status")
    t, r = re.search(r"Payload tx:\s+(\d+) B/s", dds), re.search(r"Payload rx:\s+(\d+) B/s", dds)
    if t:
        out["dds_tx_Bps"], out["dds_rx_Bps"] = float(t.group(1)), float(r.group(1))
    return out


def uorb_rates(names):
    rates = {}
    for line in px4("uorb top -1").splitlines():
        f = line.replace("\x1b[K", "").split()
        if len(f) >= 4 and f[0] in names:
            rates[f[0]] = float(f[3])
    return rates


def vec(text, key):
    m = re.search(rf"\n\s+{key}: \[([^\]]+)\]", text)
    return [float(x) for x in m.group(1).split(",")] if m else None


def read_odometry(expected):
    """What PX4 actually holds after the external-vision stream, compared with the pose we meant to send."""
    for topic in ("vehicle_visual_odometry", "vehicle_mocap_odometry"):
        txt = px4(f"listener {topic} -n 1")
        if "position:" not in txt:
            continue
        pos, q, vel, w = vec(txt, "position"), vec(txt, "q"), vec(txt, "velocity"), vec(txt, "angular_velocity")
        ts = re.search(r"timestamp: (\d+)", txt)
        tss = re.search(r"timestamp_sample: (\d+)", txt)
        res = {"topic": topic, "pose_frame": int(re.search(r"pose_frame: (\d+)", txt).group(1)),
               "velocity_frame": int(re.search(r"velocity_frame: (\d+)", txt).group(1)),
               "quality": int(re.search(r"quality: (-?\d+)", txt).group(1)), "position": pos, "q": q, "velocity": vel,
               "angular_velocity": w}
        if ts and tss:
            res["px4_delay_us"] = int(ts.group(1)) - int(tss.group(1))
        if pos:
            res["pos_err_m"] = float(np.max(np.abs(np.array(pos) - np.array(expected["pos_ned"]))))
            qe, qm = np.array(expected["q_wxyz"]), np.array(q)
            qe, qm = qe / np.linalg.norm(qe), qm / np.linalg.norm(qm)
            res["att_err_deg"] = float(np.degrees(2 * np.arccos(min(1.0, abs(float(qe @ qm))))))   # angle between two unit quaternions
            res["vel_err"] = float(np.max(np.abs(np.array(vel) - np.array(expected["vel_frd"]))))
            res["angvel_err"] = float(np.max(np.abs(np.array(w) - np.array(expected["angvel_frd"]))))
        return res
    return {"topic": None}


def run_phase(method, phase_key, repeat):
    load = phase_key.endswith("_load")
    kind = "offboard" if phase_key.startswith("offboard") else phase_key.replace("_load", "")
    args = PHASES[phase_key]
    px4_up()
    time.sleep(2)
    argv = " ".join(f"--{k} {v}" for k, v in args.items())
    pin = "taskset -c 22,23 " if load else ""
    if load:   # two busy loops, one per pinned core: the cores the client and its bridge share are fully loaded
        sh(f"docker exec -d {COMPANION} bash -c 'for c in 22 23; do taskset -c $c python3 -c \"while True: pass\" & done; wait'")
    cmd = f"docker exec {COMPANION} bash -c \"{ENV} && {pin}python3 bench.py --method {method} --phase {kind} {argv}\""
    t0 = time.time()
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines, started = [], threading.Event()

    def reader():
        for ln in proc.stdout:
            lines.append(ln)
            if ln.startswith("PHASE_START"):
                started.set()
    threading.Thread(target=reader, daemon=True).start()
    px4_side = {}
    if started.wait(120):
        dur = args.get("seconds", 0)
        if kind == "odom":
            time.sleep(dur * 0.45)
            px4_side["odometry"] = read_odometry(EXPECTED)
            px4_side["rates"] = uorb_rates({"vehicle_visual_odometry", "vehicle_mocap_odometry"})
            px4_side["bandwidth"] = px4_bandwidth()
        elif kind == "offboard":
            time.sleep(dur * 0.5)
            # offboard_control_mode is published once per received setpoint by both the MAVLink receiver and the DDS client
            # (trajectory_setpoint is also re-published by the offboard flight task, which inflates it ~3x)
            px4_side["rates"] = uorb_rates({"trajectory_setpoint", "offboard_control_mode"})
            st = px4("commander status")
            px4_side["armed"] = "Armed" in st and "Disarmed" not in st
            px4_side["nav_state"] = (re.search(r"navigation mode: (\w+)", st) or [None, None])[1]
            px4_side["bandwidth"] = px4_bandwidth()
        elif kind in ("idle", "telemetry"):
            time.sleep(dur * 0.5)
            px4_side["bandwidth"] = px4_bandwidth()
    proc.wait(timeout=240)
    if load:
        sh(f"docker exec {COMPANION} pkill -f 'while True: pass'")
    out = "".join(lines).strip().splitlines()
    try:
        res = json.loads(out[-1])
    except Exception:  # noqa: BLE001
        res = {"error": "\n".join(out[-6:])}
    res.pop("expected", None)
    res.update(method=method, phase=phase_key, repeat=repeat, px4=px4_side, wall_s=round(time.time() - t0, 1))
    return res


EXPECTED = {}


def main():
    global EXPECTED
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=METHODS)
    ap.add_argument("--phases", nargs="+", default=list(PHASES))
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    probe = sh(f"docker exec {COMPANION} bash -c \"{ENV} && python3 -c 'import bench,json; print(json.dumps(bench.EXPECTED))'\"")
    EXPECTED = json.loads(probe.strip().splitlines()[-1])
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = a.out or os.path.join(ROOT, "logs", "px4link_bench", stamp)
    os.makedirs(out, exist_ok=True)
    results = []
    for method in a.methods:
        for ph in a.phases:
            reps = a.repeats if ph in ("idle", "rtt", "odom", "telemetry") else 1
            for r in range(reps):
                print(f"[bench] {method:12s} {ph:12s} run {r + 1}/{reps}", flush=True)
                res = run_phase(method, ph, r)
                results.append(res)
                print("        ->", json.dumps({k: v for k, v in res.items() if k in ("connect_s", "rtt_ms", "error")}), flush=True)
                with open(os.path.join(out, "results.json"), "w") as f:
                    json.dump(results, f, indent=1)
    subprocess.run(["docker", "rm", "-f", "bisg-px4-sih"], capture_output=True)
    print(f"[bench] done: {out}/results.json")


if __name__ == "__main__":
    main()
