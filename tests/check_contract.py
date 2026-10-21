#!/usr/bin/env python3
"""
Phase 3 exit test (docs/roadmap.md): the live ROS graph of drone N against docs/interface-contract.md.

The topic table is read from the contract itself ("Topics — provided by the vehicle"), so the test cannot drift from it.
The four parity checks of the contract:
  1. every provided topic exists with the listed type
  2. measured rate within +-30 % of the listed rate (sim time when /clock is published, so a 0.4x sim is judged fairly;
     a rate marked "wall" comes from a wall-clock timer and is measured in wall time)
  3. TF chain map -> odom -> base_link -> zed_camera_link -> zed_left_camera_frame_optical resolvable
  4. camera_info: left/right same size as the images, stereo baseline -P[0,3]/P[0,0] = 63 mm (ZED Mini)
Row rules: Notes containing "optional" or "may be empty" may be absent / silent (SKIP); a row whose real source is "none on the
real drone" is skipped with --real; a type whose package is not built yet (bisg_msgs, Phase 2 deliverable) is PENDING.

    docker exec bisg-ros bash -c 'source /opt/ros/jazzy/setup.bash && python3 /workspace/tests/check_contract.py --drone 1'
Exit code 0 = no FAIL (SKIP / PENDING allowed).
"""
import argparse
import importlib
import math
import pathlib
import re
import sys
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.time import Time

CONTRACT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "interface-contract.md"
TF_CHAIN = ["map", "odom", "base_link", "zed_camera_link", "zed_left_camera_frame_optical"]
BASELINE_M, BASELINE_TOL = 0.063, 0.002
RATE_TOL = 0.30


def parse_contract(path):
    """Rows of the 'provided by the vehicle' table: dicts topic, type, rate (lo, hi Hz | None), source, notes."""
    text = path.read_text()
    section = text.split("## Topics — provided by the vehicle", 1)[1].split("\n## ", 1)[0]
    rows, last_rate = [], None
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0].startswith("`"):
            continue
        topic, typ, rate, source, notes = cells[0], cells[1], cells[2], cells[3], " | ".join(cells[4:])
        rng = parse_rate(rate)
        if rng is None and rate.startswith("same"):
            rng = last_rate
        last_rate = rng or last_rate
        for t in re.findall(r"`([^`]+)`", topic):
            rows.append({"topic": t, "type": (re.findall(r"`([^`]+)`", typ) or [""])[0], "rate": rng, "rate_text": rate,
                         "source": source, "notes": notes})
    return rows


def parse_rate(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*Hz", text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"≤\s*(\d+(?:\.\d+)?)\s*Hz", text)
    if m:
        return 0.0, float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*Hz", text)
    if m:
        return float(m.group(1)), float(m.group(1))
    return None


def msg_class(type_str):
    pkg, name = type_str.split("/")[0], type_str.split("/")[-1]
    try:
        return getattr(importlib.import_module(f"{pkg}.msg"), name)
    except (ImportError, AttributeError):
        return None


class Checker:
    def __init__(self, ns, seconds, real):
        self.ns, self.seconds, self.real = ns, seconds, real
        self.node = rclpy.create_node("check_contract")
        self.results = []                                   # (status, check, subject, detail)
        self.clock = None
        from rosgraph_msgs.msg import Clock
        self.node.create_subscription(Clock, "/clock", self._on_clock, 10)

    def _on_clock(self, m):
        self.clock = m.clock.sec + m.clock.nanosec * 1e-9

    def add(self, status, check, subject, detail=""):
        self.results.append((status, check, subject, detail))

    def spin(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    # --- 1 + 2: topics, types, rates ---------------------------------------------------------------------------------
    def topics(self, rows):
        self.spin(2.0)                                      # discovery + first /clock
        graph = {name: [t.replace("/msg/", "/") for t in types] for name, types in self.node.get_topic_names_and_types()}
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE)
        counts, measured = {}, []
        for r in rows:
            if r["topic"] in ("tf", "tf_static"):
                continue                                    # check 3
            name = f"{self.ns}/{r['topic']}"
            optional = re.search(r"\boptional\b|may be empty", r["notes"], re.I) is not None
            if self.real and "none on the real drone" in r["source"]:
                self.add("SKIP", "topic", name, "sim only")
                continue
            cls = msg_class(r["type"])
            if cls is None:
                self.add("PENDING", "topic", name, f"{r['type']} not built yet")
                continue
            if name not in graph:
                self.add("SKIP" if optional else "FAIL", "topic", name, "absent" + (" (optional)" if optional else ""))
                continue
            if r["type"] not in graph[name]:
                self.add("FAIL", "type", name, f"{graph[name]} != {r['type']}")
                continue
            self.add("PASS", "type", name, r["type"])
            if r["rate"] is None:
                continue
            counts[name] = 0
            self.node.create_subscription(cls, name, lambda _m, n=name: counts.__setitem__(n, counts[n] + 1), qos, raw=True)
            measured.append((name, r, optional))
        self.spin(2.0)                                      # lazy publishers ("only while subscribed") start now
        for n in counts:
            counts[n] = 0
        w0, c0 = time.time(), self.clock
        self.spin(self.seconds)
        wall, sim = time.time() - w0, (self.clock - c0) if (self.clock is not None and c0 is not None) else None
        span = sim if sim and sim > 0 else wall
        clock_note = f"sim time ({sim / wall:.2f}x real)" if sim else "wall time"
        for name, r, optional in measured:
            wall_rate = re.search(r"\bwall\b", r["rate_text"]) is not None
            hz = counts[name] / (wall if wall_rate else span)
            note = "wall time" if wall_rate else clock_note
            lo, hi = r["rate"]
            ok = hz > 0 and hz >= lo * (1 - RATE_TOL) and hz <= hi * (1 + RATE_TOL)
            status = "PASS" if ok else ("SKIP" if optional and hz == 0 else "FAIL")
            self.add(status, "rate", name, f"{hz:.1f} Hz {note}, contract {r['rate_text']}")

    # --- 3: TF chain -------------------------------------------------------------------------------------------------
    def tf(self, prefix):
        from tf2_ros import Buffer, TransformListener
        buf = Buffer()
        TransformListener(buf, self.node)
        self.spin(3.0)
        frames = [f"{prefix}{f}" for f in TF_CHAIN]
        for parent, child in zip(frames, frames[1:]):
            ok = buf.can_transform(parent, child, Time())
            self.add("PASS" if ok else "FAIL", "tf", f"{parent} -> {child}", "" if ok else "not resolvable")

    # --- 4: camera_info ----------------------------------------------------------------------------------------------
    def camera_info(self):
        from sensor_msgs.msg import CameraInfo
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        info = {}
        for side in ("left", "right"):
            self.node.create_subscription(CameraInfo, f"{self.ns}/zed/zed_node/{side}/color/rect/camera_info",
                                          lambda m, s=side: info.__setitem__(s, m), qos)
        end = time.time() + 10
        while time.time() < end and len(info) < 2:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        if len(info) < 2:
            self.add("FAIL", "camera_info", "left/right", f"received {sorted(info)} in 10 s")
            return
        l, r = info["left"], info["right"]
        same = (l.width, l.height) == (r.width, r.height)
        self.add("PASS" if same else "FAIL", "camera_info", "size", f"left {l.width}x{l.height}, right {r.width}x{r.height}")
        base = -r.p[3] / r.p[0] if r.p[0] else math.nan
        ok = abs(base - BASELINE_M) <= BASELINE_TOL
        self.add("PASS" if ok else "FAIL", "camera_info", "baseline", f"{base * 1000:.1f} mm (ZED Mini 63 mm), fx {l.k[0]:.1f} px")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=10.0, help="rate window (wall seconds)")
    ap.add_argument("--real", action="store_true", help="real drone: skip sim-only rows")
    ap.add_argument("--tf-prefix", default="", help="frame prefix to expect, e.g. drone_1/ (contract) — the wrapper has none (B16)")
    ap.add_argument("--contract", default=str(CONTRACT))
    a = ap.parse_args()

    rclpy.init()
    c = Checker(f"/drone_{a.drone}", a.seconds, a.real)
    try:
        c.topics(parse_contract(pathlib.Path(a.contract)))
        c.tf(a.tf_prefix)
        c.camera_info()
    finally:
        c.node.destroy_node()
        rclpy.try_shutdown()
    width = max(len(s) for _, _, s, _ in c.results)
    for status, check, subject, detail in c.results:
        print(f"  {status:7s} {check:11s} {subject:<{width}}  {detail}", flush=True)
    n = {k: sum(1 for r in c.results if r[0] == k) for k in ("PASS", "FAIL", "SKIP", "PENDING")}
    print(f"[check_contract] {n['PASS']} pass, {n['FAIL']} fail, {n['SKIP']} skip, {n['PENDING']} pending — "
          f"{'PASS' if not n['FAIL'] else 'FAIL'}", flush=True)
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
