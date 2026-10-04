#!/usr/bin/env python3
"""ZED module test + benchmark — one wrapper, every SDK module in turn. Runs inside the ZED container:

    ./bisg zed bench                  # fresh SDK sim -> wrapper on a derived config -> this script -> docs table
    python3 tests/zed_bench.py --drone 1 --window 20 --json out/zed_bench.json     # by hand, wrapper already up

Per phase it subscribes ONLY to that module's topics (the wrapper computes a product only while someone listens), lets it warm up,
then measures a window and reports
  function  does it publish, with sane content (PASS / FAIL / WARN / SKIP + why)
  rate      messages/s in wall time and per SIMULATED second (the sim runs ~0.4x real time, so wall Hz understates the camera)
  cost      wrapper CPU (cores, from /proc), RSS, GPU utilisation and memory (whole GPU: includes the sim, so compare to `idle`),
            sim real-time factor (the SDK's GPU load slows the sim down)
Modules that need no extra subscription but a runtime switch (mapping, object/body detection, streaming) are turned on through the
wrapper's enable_* services and off again afterwards. Heavy AI models download + optimise on first use (minutes): the timeout is long.
Needs the bench config (`./bisg zed bench` builds it): every publish_* switch advertised.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from rosidl_runtime_py.utilities import get_message
from std_srvs.srv import SetBool

BEST = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
RELIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
CLK = os.sysconf("SC_CLK_TCK")


# ---------------------------------------------------------------------------------------------- resource sampling
def wrapper_pids():
    pids = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                cmd = open(f"/proc/{d}/cmdline", "rb").read().replace(b"\0", b" ").decode()
            except OSError:
                continue
            if "component_container" in cmd and "ros2 launch" not in cmd:
                pids.append(int(d))
    return pids


def cpu_ticks(pids):
    t = 0
    for p in pids:
        try:
            f = open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()
            t += int(f[11]) + int(f[12])
        except OSError:
            pass
    return t


def rss_mb(pids):
    kb = 0
    for p in pids:
        try:
            for line in open(f"/proc/{p}/status"):
                if line.startswith("VmRSS"):
                    kb += int(line.split()[1])
        except OSError:
            pass
    return kb / 1024.0


def gpu_sample():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.split("\n")[0].split(",")
        return float(out[0]), float(out[1])
    except Exception:
        return math.nan, math.nan


# ---------------------------------------------------------------------------------------------- node
class Bench(Node):
    def __init__(self, drone):
        super().__init__("zed_bench")
        self.drone = drone
        self.root = f"/drone_{drone}/zed/zed_node/"
        self.sim_t = None
        self.sim_stamps = []
        self.create_subscription(Clock, "/clock", self._on_clock, RELIABLE)
        self.subs, self.count, self.last, self.bytes = {}, {}, {}, {}
        self.pub_click = self.create_publisher(PointStamped, "/clicked_point", RELIABLE)

    def _on_clock(self, msg):
        self.sim_t = msg.clock.sec + msg.clock.nanosec * 1e-9

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def topic_type(self, suffix):
        for name, types in self.get_topic_names_and_types():
            if name == self.root + suffix:
                return types[0]
        return None

    def listen(self, suffixes):
        missing = []
        for s in suffixes:
            t = self.topic_type(s)
            if t is None:
                missing.append(s)
                continue
            self.count[s], self.bytes[s], self.last[s] = 0, 0, None
            self.subs[s] = self.create_subscription(get_message(t), self.root + s, self._cb(s), BEST)
        return missing

    def _cb(self, s):
        def cb(msg):
            self.count[s] += 1
            self.last[s] = msg
            self.bytes[s] += len(getattr(msg, "data", b"")) if hasattr(msg, "data") and not isinstance(getattr(msg, "data"), (int, float)) else 0
        return cb

    def unlisten(self):
        for s in list(self.subs):
            self.destroy_subscription(self.subs.pop(s))

    def call(self, srv, value, timeout):
        cli = self.create_client(SetBool, self.root + srv)
        if not cli.wait_for_service(timeout_sec=10):
            return False, "service not available"
        fut = cli.call_async(SetBool.Request(data=value))
        t0 = time.monotonic()
        while not fut.done() and time.monotonic() - t0 < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not fut.done():
            return False, f"no answer after {timeout:.0f} s"
        r = fut.result()
        return bool(r.success), r.message


# ---------------------------------------------------------------------------------------------- measurement
def measure(node, suffixes, warmup, window, setup=None):
    """Subscribe, warm up, measure a window. Returns the metrics dict (+ the last messages in node.last for checks)."""
    pids = wrapper_pids()
    missing = node.listen(suffixes)
    if setup:
        setup()
    node.spin(warmup)
    for s in suffixes:
        node.count[s], node.bytes[s] = 0, 0
    t0, sim0, ticks0 = time.monotonic(), node.sim_t, cpu_ticks(pids)
    gpu = []
    while time.monotonic() - t0 < window:
        node.spin(1.0)
        gpu.append(gpu_sample())
    dt = time.monotonic() - t0
    sim_dt = (node.sim_t - sim0) if (node.sim_t is not None and sim0 is not None) else math.nan
    m = {"missing": missing, "wall_s": round(dt, 1), "sim_s": round(sim_dt, 1), "rtf": round(sim_dt / dt, 3) if sim_dt == sim_dt else None,
         "cpu_cores": round((cpu_ticks(pids) - ticks0) / CLK / dt, 2), "rss_mb": round(rss_mb(pids)),
         "gpu_util": round(float(np.nanmean([g[0] for g in gpu])), 0), "gpu_mem_mb": round(float(np.nanmax([g[1] for g in gpu]))),
         "topics": {}}
    for s in suffixes:
        if s in missing:
            continue
        n = node.count[s]
        m["topics"][s] = {"n": n, "wall_hz": round(n / dt, 1), "sim_hz": round(n / sim_dt, 1) if sim_dt == sim_dt and sim_dt > 0 else None,
                          "mb_s": round(node.bytes[s] / dt / 1e6, 1)}
    return m


def finite_frac(arr):
    return float(np.isfinite(arr).mean())


def img32(msg):
    return np.frombuffer(bytes(msg.data), np.float32).reshape(msg.height, msg.width)


# ---------------------------------------------------------------------------------------------- checks: (status, note)
def need(node, s):
    return node.last.get(s)


def chk_images(*suffixes, size=(1280, 720)):
    def f(node, m):
        bad = []
        for s in suffixes:
            msg = need(node, s)
            if msg is None:
                bad.append(f"{s}: no message")
            elif (msg.width, msg.height) != size and "stereo" not in s:
                bad.append(f"{s}: {msg.width}x{msg.height}")
        return ("FAIL", "; ".join(bad)) if bad else ("PASS", f"{size[0]}x{size[1]}")
    return f


def chk_depth(node, m):
    msg = need(node, "depth/depth_registered")
    if msg is None or msg.encoding != "32FC1":
        return "FAIL", "no 32FC1 depth"
    d = img32(msg)
    ff = finite_frac(d)
    v = d[np.isfinite(d)]
    return ("PASS" if ff > 0.5 and v.size and 0.1 < v.min() and v.max() < 20 else "FAIL"), f"{ff:.0%} valid, {v.min():.2f}-{v.max():.2f} m"


def chk_cloud(node, m):
    msg = need(node, "point_cloud/cloud_registered")
    if msg is None:
        return "FAIL", "no cloud"
    names = [f.name for f in msg.fields]
    n = msg.width * msg.height
    return ("PASS" if {"x", "y", "z"} <= set(names) and n > 1000 else "FAIL"), f"{msg.width}x{msg.height} points, fields {','.join(names)}"


def chk_depth_extras(node, m):
    notes, st = [], "PASS"
    disp, dep = need(node, "disparity/disparity_image"), need(node, "depth/depth_registered")
    if disp is None:
        return "FAIL", "no disparity"
    dm = img32(disp.image)
    if dep is not None:
        z = img32(dep)
        # same pixels: z = f*T/d (our depth is the metric reference); compare medians over pixels valid in both
        ok = np.isfinite(dm) & np.isfinite(z) & (dm > 0) & (z > 0) & (z.shape == dm.shape)
        if ok.any():
            ratio = float(np.median((disp.f * disp.t / dm[ok]) / z[ok]))
            notes.append(f"f*T/disparity vs depth = {ratio:.3f}")
            if abs(ratio - 1) > 0.05:
                st = "FAIL"
    conf = need(node, "confidence/confidence_map")
    if conf is None:
        st, notes = "FAIL", notes + ["no confidence map"]
    else:
        c = img32(conf)
        c = c[np.isfinite(c)]
        notes.append(f"confidence {c.min():.0f}-{c.max():.0f}")
        if c.size == 0 or c.min() < 0 or c.max() > 100:
            st = "FAIL"
    info = need(node, "depth/depth_info")
    notes.append("depth_info " + (f"{info.min_depth:.2f}-{info.max_depth:.2f} m" if info is not None else "none"))
    if info is None:
        st = "FAIL"
    return st, "; ".join(notes)


def chk_roi(node, m):
    msg = need(node, "roi_mask/image")
    if msg is None:
        return "WARN", "no mask published (automatic ROI needs the camera to see parts of the robot; the sim view is clear)"
    a = np.frombuffer(bytes(msg.data), np.uint8)
    return "PASS", f"mask {msg.width}x{msg.height}, {float((a > 0).mean()):.0%} of pixels kept"


def chk_tracking(node, m):
    st = need(node, "pose/status")
    od = need(node, "odom")
    if od is None or st is None:
        return "FAIL", "no odom / pose status"
    ok = st.odometry_status == 0
    p = od.pose.pose.position
    return ("PASS" if ok else "FAIL"), f"odometry_status={st.odometry_status}, odom ({p.x:.3f}, {p.y:.3f}, {p.z:.3f}) frame {od.header.frame_id}->{od.child_frame_id}"


def chk_tracking_extras(node, m):
    notes, st = [], "PASS"
    cov = need(node, "pose_with_covariance")
    if cov is None:
        st = "FAIL"; notes.append("no pose_with_covariance")
    else:
        c = np.array(cov.pose.covariance)
        notes.append(f"cov diag x={c[0]:.2e} yaw={c[35]:.2e}")
        if not np.isfinite(c).all():
            st = "FAIL"
    for s in ("path_odom", "path_map"):
        p = need(node, s)
        notes.append(f"{s} {len(p.poses) if p is not None else 'none'} poses")
        if p is None:
            st = "FAIL"
    lm = need(node, "pose/landmarks")
    notes.append(f"landmarks {lm.width * lm.height if lm is not None else 'none'}")
    if lm is None:
        st = "WARN" if st == "PASS" else st
    return st, "; ".join(notes)


def chk_imu(node, m):
    a, b = need(node, "imu/data"), need(node, "imu/data_raw")
    if a is None:
        return "FAIL", "no imu/data"
    return ("PASS" if b is not None else "WARN"), f"imu/data ok; imu/data_raw {'ok' if b is not None else 'absent (the sim stream has no sensor channel; real camera only)'}"


def chk_mapping(node, m):
    msg = need(node, "mapping/fused_cloud")
    if msg is None:
        return "FAIL", "no fused cloud"
    n = msg.width * msg.height
    return ("PASS" if n > 100 else "FAIL"), f"{n} points, frame {msg.header.frame_id}"


def chk_plane(node, m):
    msg = need(node, "plane")
    if msg is None:
        return "FAIL", "no plane published after the clicked point (frame/point not on a plane?)"
    return "PASS", f"normal ({msg.normal.x:.2f},{msg.normal.y:.2f},{msg.normal.z:.2f}), {len(msg.mesh.triangles)} triangles"


def chk_objects(node, m):
    msg = need(node, "obj_det/objects")
    if msg is None:
        return "FAIL", "enabled but nothing published"
    return "PASS", f"{len(msg.objects)} objects in view (the room has none; this proves the model runs, not accuracy)"


def chk_skeletons(node, m):
    msg = need(node, "body_trk/skeletons")
    if msg is None:
        return "FAIL", "enabled but nothing published"
    return "PASS", f"{len(msg.objects)} skeletons in view (none in the room: runs, accuracy untested)"


# ---------------------------------------------------------------------------------------------- phases
def build_phases(node, args):
    R = "left/color/rect/image"

    def toggle(srv, on, timeout=900):
        def run():
            ok, msg = node.call(srv, on, timeout)
            node.toggle_result = (ok, msg)
        return run

    def click():
        for _ in range(5):
            p = PointStamped()
            p.header.frame_id, p.header.stamp = "odom", node.get_clock().now().to_msg()
            p.point.x, p.point.y, p.point.z = 1.5, 0.0, -0.05
            node.pub_click.publish(p)
            node.spin(0.5)

    P = []
    P.append(dict(name="idle", module="(no subscriber)", topics=[], check=lambda n, m: ("PASS", "baseline: wrapper running, nothing requested")))
    P.append(dict(name="video_left", module="video", topics=[R, "left/color/rect/camera_info"], check=chk_images(R)))
    P.append(dict(name="video_stereo", module="video", topics=[R, "right/color/rect/image", "left/color/rect/camera_info", "right/color/rect/camera_info"],
                  check=chk_images(R, "right/color/rect/image")))
    P.append(dict(name="video_variants", module="video", topics=["rgb/color/rect/image", "left/color/raw/image", "left/gray/rect/image", "stereo/color/rect/image"],
                  check=chk_images("rgb/color/rect/image", "left/color/raw/image", "left/gray/rect/image")))
    P.append(dict(name="depth", module="depth", topics=["depth/depth_registered"], check=chk_depth))
    P.append(dict(name="point_cloud", module="depth", topics=["point_cloud/cloud_registered"], check=chk_cloud))
    P.append(dict(name="depth_extras", module="depth", topics=["disparity/disparity_image", "confidence/confidence_map", "depth/depth_info", "depth/depth_registered"],
                  check=chk_depth_extras))
    P.append(dict(name="roi_mask", module="region_of_interest", topics=["roi_mask/image"], check=chk_roi))
    P.append(dict(name="tracking", module="positional_tracking", topics=["odom", "pose", "pose/status"], check=chk_tracking))
    P.append(dict(name="tracking_extras", module="positional_tracking", topics=["pose_with_covariance", "path_odom", "path_map", "pose/landmarks"],
                  check=chk_tracking_extras))
    P.append(dict(name="imu", module="sensors", topics=["imu/data", "imu/data_raw"], check=chk_imu))
    P.append(dict(name="spatial_mapping", module="spatial_mapping", topics=["mapping/fused_cloud"], setup=toggle("enable_mapping", True, 60),
                  teardown=toggle("enable_mapping", False, 60), check=chk_mapping, listen_after_setup=True, extra_warmup=10))
    P.append(dict(name="plane_detection", module="plane_detection", topics=["plane", "plane_marker"], setup=click, check=chk_plane))
    P.append(dict(name="drone_core", module="(typical drone load)", topics=[R, "right/color/rect/image", "depth/depth_registered", "point_cloud/cloud_registered", "odom", "imu/data"],
                  check=lambda n, m: ("PASS", "stereo + depth + cloud + odometry + imu together")))
    if not args.skip_ai:
        P.append(dict(name="object_detection", module="object_detection", topics=["obj_det/objects"], setup=toggle("enable_obj_det", True),
                      teardown=toggle("enable_obj_det", False, 60), check=chk_objects, listen_after_setup=True, extra_warmup=5))
        P.append(dict(name="body_tracking", module="body_tracking", topics=["body_trk/skeletons"], setup=toggle("enable_body_trk", True),
                      teardown=toggle("enable_body_trk", False, 60), check=chk_skeletons, listen_after_setup=True, extra_warmup=5))
    if args.streaming:   # opt-in: in the sim the camera is itself a stream and enabling the streaming server CRASHES the wrapper (bugs.md B19)
        P.append(dict(name="streaming", module="streaming", topics=[], setup=toggle("enable_streaming", True, 60), teardown=toggle("enable_streaming", False, 60),
                      check=lambda n, m: ("PASS", "stream server started") if getattr(n, "toggle_result", (False, ""))[0] else ("FAIL", f"enable_streaming: {n.toggle_result[1]}"),
                      listen_after_setup=True))
    return P


def run_phase(node, ph, args):
    node.last.clear()
    node.toggle_result = (True, "")
    topics = list(ph["topics"])
    pids_missing = []
    t_start = time.monotonic()
    if ph.get("listen_after_setup"):
        ph["setup"]()                       # switch on first (slow for AI models), then measure
        setup = None
    else:
        setup = ph.get("setup")
    warm = args.warmup + ph.get("extra_warmup", 0)
    m = measure(node, topics, warm, args.window, setup=setup)
    status, note = ph["check"](node, m)
    for s in m["missing"]:
        status, note = "FAIL", f"topic not advertised: {s} ({note})"
    if ph.get("teardown"):
        ph["teardown"]()
    node.unlisten()
    node.spin(2.0)
    m.update(phase=ph["name"], module=ph["module"], status=status, note=note, setup_s=round(time.monotonic() - t_start - args.window, 1))
    return m


def fmt_table(results):
    idle = next((r for r in results if r["phase"] == "idle"), None)
    L = ["| phase | module | result | rate (wall Hz / sim Hz) | wrapper CPU (cores) | RSS MB | GPU % | GPU MB (+idle) | sim RTF | note |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        rates = ", ".join(f"{k.split('/')[-1] if not k.endswith('image') else k.split('/')[0]}:{v['wall_hz']}/{v['sim_hz']}" for k, v in r["topics"].items()) or "-"
        gm = f"{r['gpu_mem_mb']:.0f} ({r['gpu_mem_mb'] - idle['gpu_mem_mb']:+.0f})" if idle else f"{r['gpu_mem_mb']:.0f}"
        L.append(f"| {r['phase']} | {r['module']} | {r['status']} | {rates} | {r['cpu_cores']} | {r['rss_mb']} | {r['gpu_util']:.0f} | {gm} | {r['rtf']} | {r['note']} |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--window", type=float, default=20.0, help="measurement window per phase, wall seconds")
    ap.add_argument("--warmup", type=float, default=6.0)
    ap.add_argument("--only", default="", help="comma list of phase names")
    ap.add_argument("--streaming", action="store_true", help="also test enable_streaming (crashes the wrapper in the sim: run it last, restart the sim after)")
    ap.add_argument("--skip-ai", action="store_true", help="skip object/body detection (model download)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    rclpy.init()
    node = Bench(args.drone)
    node.spin(3.0)
    if not any(n.endswith("zed_node") for n, _ in node.get_node_names_and_namespaces()) and node.topic_type("status/health") is None:
        print("FAIL: no ZED wrapper found (./bisg zed up)")
        return 2
    if not wrapper_pids():
        print("WARN: wrapper process not visible from here (run this inside the zed container): CPU/RSS will read 0")
    phases = build_phases(node, args)
    if args.only:
        keep = set(args.only.split(","))
        phases = [p for p in phases if p["name"] in keep or p["name"] == "idle"]
    results = []
    for ph in phases:
        print(f"[bench] {ph['name']} ...", flush=True)
        r = run_phase(node, ph, args)
        results.append(r)
        print(f"        {r['status']}: {r['note']}  | cpu {r['cpu_cores']} cores, gpu {r['gpu_util']:.0f}%, rtf {r['rtf']}", flush=True)
    print("\n" + fmt_table(results))
    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "args": vars(args), "results": results}, open(args.json, "w"), indent=1)
        print(f"\nwrote {args.json}")
    fails = [r for r in results if r["status"] == "FAIL"]
    print(f"\n{len(results) - len(fails)}/{len(results)} phases without FAIL ({sum(r['status'] == 'WARN' for r in results)} WARN)")
    node.destroy_node()
    rclpy.shutdown()
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
