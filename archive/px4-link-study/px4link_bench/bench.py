#!/usr/bin/env python3
"""
PX4 <-> companion link benchmark client: MAVROS vs MAVSDK (native 4.x and gRPC) vs uXRCE-DDS.   docs/study-px4-link.md

Runs INSIDE the companion container (image bisg/px4link-bench:jazzy). One invocation = one method + one phase; it starts that
method's bridge process itself (mavros_node / mavsdk_server / MicroXRCEAgent), so the bridge's CPU and memory are measured
apart from this client's. Prints one JSON object on the last stdout line. run.py (host) orchestrates and samples PX4.

  bench.py --method mavros|mavsdk|mavsdk_grpc|dds --phase idle|telemetry|rtt|odom|offboard [--seconds N] [--rate HZ] [--n N]

Phases (identical work for every method):
  idle       connect, then do nothing for --seconds                         -> connect time, idle CPU/RSS of the bridge
  telemetry  subscribe attitude, position/velocity, armed for --seconds     -> arrival rate + jitter per stream
  rtt        --n x "set HOLD mode" and wait for the ACK                      -> request/response round trip (p50/p95/max)
  odom       stream a fixed external-vision pose at --rate Hz               -> PX4-side check by run.py (frames, delay, values)
  offboard   arm, offboard, stream position setpoints at --rate Hz          -> PX4-side registered setpoint rate by run.py
"""
import argparse
import asyncio
import json
import math
import os
import statistics
import subprocess
import sys
import threading
import time

import numpy as np
import psutil
from scipy.spatial.transform import Rotation

# PX4 under test = SITL instance 1 (tools/px4link_bench/px4.sh): own ports, MAV_SYS_ID 2, own ROS domain (ROS_DOMAIN_ID=77 in run.py)
SYSID, MAV_PORT, MAV_REMOTE, DDS_PORT = 2, 14541, 14581, 8889

# ---------------------------------------------------------------------------------------------- shared test pose
# External-vision test pose, given the way a ROS/ZED user has it (ENU world, FLU body) ...
POS_ENU = np.array([1.0, 2.0, 3.0])
R_ENU_FLU = Rotation.from_euler("ZYX", [90.0, -5.0, 10.0], degrees=True)       # yaw, pitch, roll
V_FLU = np.array([0.5, -0.25, 0.1])                                              # body-frame linear velocity
W_FLU = np.array([0.02, -0.01, 0.03])                                            # body-frame angular velocity
# ... and what PX4 must end up with (NED world, FRD body):
M = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1.0]])                               # ENU -> NED
D = np.diag([1.0, -1.0, -1.0])                                                   # FLU -> FRD
POS_NED = M @ POS_ENU
R_NED_FRD = Rotation.from_matrix(M @ R_ENU_FLU.as_matrix() @ D)
V_FRD, W_FRD = D @ V_FLU, D @ W_FLU
EXPECTED = {"pos_ned": POS_NED.tolist(), "q_wxyz": [R_NED_FRD.as_quat()[3], *R_NED_FRD.as_quat()[:3]],
            "vel_frd": V_FRD.tolist(), "angvel_frd": W_FRD.tolist()}
TARGET_NED = (0.0, 0.0, -2.0)   # offboard hover point


WARMUP_S = 6.0      # let the connect-time burst (parameter download, stream setup) pass before steady-state sampling


def cpu_seconds(pids):
    """Cumulative CPU time (user+system, s) of these processes and their descendants."""
    total = 0.0
    for pid in pids:
        try:
            p = psutil.Process(pid)
            for q in [p] + p.children(recursive=True):
                t = q.cpu_times()
                total += t.user + t.system
        except psutil.Error:
            pass
    return round(total, 2)


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def arrival_stats(ts):
    """Rate and jitter of a list of arrival times (s)."""
    if len(ts) < 3:
        return {"n": len(ts), "hz": 0.0}
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    span = ts[-1] - ts[0]
    return {"n": len(ts), "hz": round((len(ts) - 1) / span, 2) if span > 0 else 0.0,
            "gap_p50_ms": round(pct(gaps, 50) * 1e3, 2), "gap_p95_ms": round(pct(gaps, 95) * 1e3, 2),
            "gap_max_ms": round(max(gaps) * 1e3, 2), "gap_std_ms": round(statistics.pstdev(gaps) * 1e3, 2)}


class Sampler(threading.Thread):
    """CPU (percent of one core) and RSS of the bridge process tree vs this client, sampled every 0.5 s."""

    def __init__(self, bridge_pids):
        super().__init__(daemon=True)
        self.bridge = [psutil.Process(p) for p in bridge_pids]
        self.me = psutil.Process()
        self.rows, self._halt, self.cache = [], threading.Event(), {}
        for p in self.bridge + [self.me]:
            p.cpu_percent(None)

    def run(self):
        while not self._halt.wait(0.5):
            try:
                tree = self._tree(self.bridge)
                b_cpu = sum(p.cpu_percent(None) for p in tree)
                b_rss = sum(p.memory_info().rss for p in tree)
                self.rows.append((b_cpu, b_rss, self.me.cpu_percent(None), self.me.memory_info().rss))
            except psutil.Error:
                pass

    def _tree(self, procs):
        """The processes plus their descendants, as cached psutil objects (cpu_percent needs the same object each call)."""
        out = []
        for p in procs:
            try:
                for q in [p] + p.children(recursive=True):
                    if q.pid not in self.cache:
                        self.cache[q.pid] = q
                        q.cpu_percent(None)          # prime: this object reports from now on
                    out.append(self.cache[q.pid])
            except psutil.Error:
                pass
        return out

    def summary(self):
        self._halt.set()
        if not self.rows:
            return {}
        cols = list(zip(*self.rows))
        mean = lambda c: round(sum(c) / len(c), 1)   # noqa: E731
        return {"bridge_cpu_pct_mean": mean(cols[0]), "bridge_cpu_pct_max": round(max(cols[0]), 1),
                "bridge_rss_mb": round(max(cols[1]) / 2 ** 20, 1),
                "client_cpu_pct_mean": mean(cols[2]), "client_rss_mb": round(max(cols[3]) / 2 ** 20, 1)}


def spawn(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)


def kill(proc):
    try:
        os.killpg(os.getpgid(proc.pid), 15)
        proc.wait(5)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------------------------- ROS 2 based: MAVROS, DDS
def ros_env():
    import rclpy  # noqa: WPS433
    rclpy.init()
    return rclpy


class RosBase:
    def __init__(self):
        self.rclpy = ros_env()
        self.node = self.rclpy.create_node("px4link_bench")
        self.t0 = time.time()
        self._spin = threading.Thread(target=lambda: self.rclpy.spin(self.node), daemon=True)
        self._spin.start()

    def stop_ros(self):
        self.rclpy.try_shutdown()


class Mavros(RosBase):
    name = "mavros"
    lean = False

    def start(self):
        lists = "/workspace/tools/px4link_bench/mavros_lean.yaml" if self.lean else "/opt/ros/jazzy/share/mavros/launch/px4_pluginlists.yaml"
        self.bridge = spawn(["ros2", "run", "mavros", "mavros_node", "--ros-args", "-r", "__ns:=/",
                             "-p", f"fcu_url:=udp://:{MAV_PORT}@127.0.0.1:{MAV_REMOTE}", "-p", f"tgt_system:={SYSID}", "-p", "fcu_protocol:=v2.0",
                             "--params-file", lists,
                             "--params-file", "/opt/ros/jazzy/share/mavros/launch/px4_config.yaml"])
        from mavros_msgs.msg import State
        self.state = None
        self.node.create_subscription(State, "/mavros/state", lambda m: setattr(self, "state", m), 10)
        return [self.bridge.pid]

    def wait_connected(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if self.state is not None and self.state.connected:
                return time.time() - self.t0
            time.sleep(0.05)
        raise SystemExit("mavros: never connected")

    def telemetry(self, seconds):
        from rclpy.qos import qos_profile_sensor_data
        from geometry_msgs.msg import PoseStamped
        from mavros_msgs.msg import State
        from sensor_msgs.msg import Imu
        rec = {"attitude": [], "position": [], "armed_state": []}
        self.node.create_subscription(Imu, "/mavros/imu/data", lambda m: rec["attitude"].append(time.time()), qos_profile_sensor_data)
        self.node.create_subscription(PoseStamped, "/mavros/local_position/pose", lambda m: rec["position"].append(time.time()), qos_profile_sensor_data)
        self.node.create_subscription(State, "/mavros/state", lambda m: rec["armed_state"].append(time.time()), 10)
        time.sleep(seconds)
        return {k: arrival_stats(v) for k, v in rec.items()}

    def rtt(self, n):
        from mavros_msgs.srv import CommandLong
        cli = self.node.create_client(CommandLong, "/mavros/cmd/command")
        cli.wait_for_service(20)
        req = CommandLong.Request(command=176, param1=1.0, param2=4.0, param3=3.0)   # DO_SET_MODE custom AUTO.LOITER (= HOLD)
        out = []
        for _ in range(n):
            t = time.perf_counter()
            ev = threading.Event()
            fut = cli.call_async(req)
            fut.add_done_callback(lambda f: ev.set())
            ev.wait(5)
            if fut.done() and fut.result() is not None and fut.result().success:
                out.append(time.perf_counter() - t)
            time.sleep(0.02)
        return out

    def odom(self, seconds, rate):
        from nav_msgs.msg import Odometry
        pub = self.node.create_publisher(Odometry, "/mavros/odometry/out", 10)
        q = R_ENU_FLU.as_quat()
        end, dt, sent = time.time() + seconds, 1.0 / rate, 0
        while time.time() < end:
            m = Odometry()
            m.header.stamp = self.node.get_clock().now().to_msg()
            m.header.frame_id, m.child_frame_id = "odom", "base_link"
            m.pose.pose.position.x, m.pose.pose.position.y, m.pose.pose.position.z = POS_ENU.tolist()
            m.pose.pose.orientation.x, m.pose.pose.orientation.y, m.pose.pose.orientation.z, m.pose.pose.orientation.w = q.tolist()
            m.twist.twist.linear.x, m.twist.twist.linear.y, m.twist.twist.linear.z = V_FLU.tolist()
            m.twist.twist.angular.x, m.twist.twist.angular.y, m.twist.twist.angular.z = W_FLU.tolist()
            pub.publish(m)
            sent += 1
            time.sleep(dt)
        return {"sent": sent}

    def offboard(self, seconds, rate):
        from geometry_msgs.msg import PoseStamped
        from mavros_msgs.srv import CommandBool, SetMode
        pub = self.node.create_publisher(PoseStamped, "/mavros/setpoint_position/local", 10)
        sent = [0]
        stop = threading.Event()

        def stream():
            dt, nxt = 1.0 / rate, time.perf_counter()
            while not stop.is_set():
                m = PoseStamped()
                m.header.stamp = self.node.get_clock().now().to_msg()
                m.header.frame_id = "map"
                m.pose.position.z = 2.0
                m.pose.orientation.w = 1.0
                pub.publish(m)
                sent[0] += 1
                nxt += dt
                time.sleep(max(0.0, nxt - time.perf_counter()))
        th = threading.Thread(target=stream, daemon=True)
        th.start()
        time.sleep(1.5)
        for srv, typ, req in (("/mavros/set_mode", SetMode, SetMode.Request(custom_mode="OFFBOARD")),
                              ("/mavros/cmd/arming", CommandBool, CommandBool.Request(value=True))):
            cli = self.node.create_client(typ, srv)
            cli.wait_for_service(10)
            fut = cli.call_async(req)
            end = time.time() + 5
            while not fut.done() and time.time() < end:
                time.sleep(0.02)
        sent[0] = 0
        t0 = time.time()
        time.sleep(seconds)
        stop.set()
        return {"sent": sent[0], "sent_hz": round(sent[0] / (time.time() - t0), 1)}


class MavrosLean(Mavros):
    name = "mavros_lean"
    lean = True


class Dds(RosBase):
    name = "dds"

    def start(self):
        self.bridge = spawn(["MicroXRCEAgent", "udp4", "-p", str(DDS_PORT)])
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
        self.qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                              history=HistoryPolicy.KEEP_LAST, depth=1)
        from px4_msgs.msg import VehicleStatus
        self.seen = False
        self.node.create_subscription(VehicleStatus, "/fmu/out/vehicle_status_v1", lambda m: setattr(self, "seen", True), self.qos)
        return [self.bridge.pid]

    def wait_connected(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if self.seen:
                return time.time() - self.t0
            time.sleep(0.05)
        raise SystemExit("dds: no data from PX4")

    def now_us(self):
        return int(self.node.get_clock().now().nanoseconds / 1000)

    def telemetry(self, seconds):
        from px4_msgs.msg import VehicleAttitude, VehicleLocalPosition, VehicleStatus
        rec = {"attitude": [], "position": [], "armed_state": []}
        self.node.create_subscription(VehicleAttitude, "/fmu/out/vehicle_attitude", lambda m: rec["attitude"].append(time.time()), self.qos)
        self.node.create_subscription(VehicleLocalPosition, "/fmu/out/vehicle_local_position_v1", lambda m: rec["position"].append(time.time()), self.qos)
        self.node.create_subscription(VehicleStatus, "/fmu/out/vehicle_status_v1", lambda m: rec["armed_state"].append(time.time()), self.qos)
        time.sleep(seconds)
        return {k: arrival_stats(v) for k, v in rec.items()}

    def _cmd(self, pub, command, p1=0.0, p2=0.0, p3=0.0):
        from px4_msgs.msg import VehicleCommand
        m = VehicleCommand()
        m.timestamp = self.now_us()
        m.command, m.param1, m.param2, m.param3 = command, float(p1), float(p2), float(p3)
        m.target_system, m.source_system = SYSID, 1
        m.target_component = m.source_component = 1
        m.from_external = True
        pub.publish(m)

    def rtt(self, n):
        from px4_msgs.msg import VehicleCommand, VehicleCommandAck
        pub = self.node.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", self.qos)
        acks = []
        ev = threading.Event()

        def on_ack(m):
            if m.command == 176:
                acks.append(time.perf_counter())
                ev.set()
        self.node.create_subscription(VehicleCommandAck, "/fmu/out/vehicle_command_ack", on_ack, self.qos)
        time.sleep(1.0)
        out = []
        for _ in range(n):
            ev.clear()
            t = time.perf_counter()
            self._cmd(pub, 176, 1, 4, 3)
            if ev.wait(5):
                out.append(acks[-1] - t)
            time.sleep(0.02)
        return out

    def odom(self, seconds, rate):
        from px4_msgs.msg import VehicleOdometry
        pub = self.node.create_publisher(VehicleOdometry, "/fmu/in/vehicle_visual_odometry", self.qos)
        q = R_NED_FRD.as_quat()
        end, dt, sent = time.time() + seconds, 1.0 / rate, 0
        while time.time() < end:
            m = VehicleOdometry()
            m.timestamp = m.timestamp_sample = self.now_us()
            m.pose_frame = VehicleOdometry.POSE_FRAME_NED
            m.position = [float(x) for x in POS_NED]
            m.q = [float(q[3]), float(q[0]), float(q[1]), float(q[2])]
            m.velocity_frame = VehicleOdometry.VELOCITY_FRAME_BODY_FRD
            m.velocity = [float(x) for x in V_FRD]
            m.angular_velocity = [float(x) for x in W_FRD]
            m.position_variance = m.orientation_variance = m.velocity_variance = [0.01, 0.01, 0.01]
            m.quality = 100
            pub.publish(m)
            sent += 1
            time.sleep(dt)
        return {"sent": sent}

    def offboard(self, seconds, rate):
        from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand
        p_mode = self.node.create_publisher(OffboardControlMode, "/fmu/in/offboard_control_mode", self.qos)
        p_sp = self.node.create_publisher(TrajectorySetpoint, "/fmu/in/trajectory_setpoint", self.qos)
        p_cmd = self.node.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", self.qos)
        sent = [0]
        stop = threading.Event()

        def stream():
            dt, nxt = 1.0 / rate, time.perf_counter()
            while not stop.is_set():
                a = OffboardControlMode()
                a.timestamp = self.now_us()
                a.position = True
                p_mode.publish(a)
                s = TrajectorySetpoint()
                s.timestamp = self.now_us()
                s.position = [float(x) for x in TARGET_NED]
                s.yaw = 0.0
                p_sp.publish(s)
                sent[0] += 1
                nxt += dt
                time.sleep(max(0.0, nxt - time.perf_counter()))
        th = threading.Thread(target=stream, daemon=True)
        th.start()
        time.sleep(1.5)
        self._cmd(p_cmd, 176, 1, 6)              # DO_SET_MODE custom OFFBOARD
        time.sleep(0.3)
        self._cmd(p_cmd, 400, 1)                 # arm
        time.sleep(1.0)
        sent[0] = 0
        t0 = time.time()
        time.sleep(seconds)
        stop.set()
        return {"sent": sent[0], "sent_hz": round(sent[0] / (time.time() - t0), 1)}


# ---------------------------------------------------------------------------------------------- MAVSDK (native + gRPC)
class MavsdkNative:
    name = "mavsdk"

    def start(self):
        self.t0 = time.time()
        return []            # no separate process: the library runs inside the client

    async def connect(self):
        from mavsdk.asyncio import Mavsdk, Configuration, ComponentType
        from mavsdk.asyncio.plugins.action import ActionAsync
        from mavsdk.asyncio.plugins.telemetry import TelemetryAsync
        from mavsdk.asyncio.plugins.mocap import MocapAsync
        from mavsdk.asyncio.plugins.offboard import OffboardAsync
        self.mavsdk = Mavsdk(Configuration.create_with_component_type(ComponentType.COMPANION_COMPUTER))
        await self.mavsdk.add_any_connection(f"udpin://0.0.0.0:{MAV_PORT}")
        self.drone = await self.mavsdk.first_autopilot(timeout_s=60.0)
        if self.drone is None:
            raise SystemExit("mavsdk: no autopilot")
        self.action, self.telemetry_, self.mocap, self.offb = (ActionAsync(self.drone), TelemetryAsync(self.drone),
                                                              MocapAsync(self.drone), OffboardAsync(self.drone))
        return time.time() - self.t0

    async def telemetry(self, seconds):
        rec = {"attitude": [], "position": [], "armed_state": []}

        async def sub(gen, key):
            async for _ in gen:
                rec[key].append(time.time())
        tasks = [asyncio.create_task(sub(self.telemetry_.subscribe_attitude_quaternion(), "attitude")),
                 asyncio.create_task(sub(self.telemetry_.subscribe_position_velocity_ned(), "position")),
                 asyncio.create_task(sub(self.telemetry_.subscribe_armed(), "armed_state"))]
        await asyncio.sleep(seconds)
        for t in tasks:
            t.cancel()
        return {k: arrival_stats(v) for k, v in rec.items()}

    async def rtt(self, n):
        out = []
        for _ in range(n):
            t = time.perf_counter()
            try:
                await self.action.hold()
                out.append(time.perf_counter() - t)
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.02)
        return out

    def _odometry(self, mod):
        q = R_NED_FRD.as_quat()
        cov = mod.Covariance([float("nan")])
        return mod.Odometry(
            time_usec=int(time.time() * 1e6), frame_id=getattr(mod.Odometry.MavFrame, os.environ.get("BENCH_FRAME", "LOCAL_FRD")),
            position_body=mod.PositionBody(*[float(x) for x in POS_NED]),
            q=mod.Quaternion(float(q[3]), float(q[0]), float(q[1]), float(q[2])),
            speed_body=mod.SpeedBody(*[float(x) for x in V_FRD]),
            angular_velocity_body=mod.AngularVelocityBody(*[float(x) for x in W_FRD]),
            pose_covariance=cov, velocity_covariance=cov, reset_counter=0,
            estimator_type=mod.Odometry.MavEstimatorType.VISION, quality_percent=100)

    async def odom(self, seconds, rate):
        from mavsdk.asyncio.plugins import mocap as mod
        end, dt, sent = time.time() + seconds, 1.0 / rate, 0
        while time.time() < end:
            await self.mocap.set_odometry(self._odometry(mod))
            sent += 1
            await asyncio.sleep(dt)
        return {"sent": sent}

    def _pos_cls(self):
        from mavsdk.asyncio.plugins.offboard import PositionNedYaw
        return PositionNedYaw

    async def offboard(self, seconds, rate):
        sp = self._pos_cls()(*TARGET_NED, 0.0)
        await self.offb.set_position_ned(sp)
        sent = [0]
        stop = asyncio.Event()

        async def stream():
            dt, nxt = 1.0 / rate, time.perf_counter()
            while not stop.is_set():
                await self.offb.set_position_ned(sp)
                sent[0] += 1
                nxt += dt
                await asyncio.sleep(max(0.0, nxt - time.perf_counter()))
        task = asyncio.create_task(stream())
        await asyncio.sleep(1.0)
        await self.offb.start()
        await self.action.arm()
        await asyncio.sleep(1.0)
        sent[0] = 0
        t0 = time.time()
        await asyncio.sleep(seconds)
        stop.set()
        await task
        return {"sent": sent[0], "sent_hz": round(sent[0] / (time.time() - t0), 1)}


class MavsdkGrpc(MavsdkNative):
    name = "mavsdk_grpc"

    def start(self):
        self.t0 = time.time()
        return []

    async def connect(self):
        import mavsdk_grpc
        self.mod = mavsdk_grpc
        self.drone = mavsdk_grpc.System()
        await self.drone.connect(system_address=f"udpin://0.0.0.0:{MAV_PORT}")
        async for s in self.drone.core.connection_state():
            if s.is_connected:
                break
        self.action, self.mocap, self.offb = self.drone.action, self.drone.mocap, self.drone.offboard
        # the gRPC server is a child process of this client; the Sampler attaches to it afterwards (bridge_pids())
        return time.time() - self.t0

    def bridge_pids(self):
        return [c.pid for c in psutil.Process().children(recursive=True) if "mavsdk_server" in " ".join(c.cmdline())]

    async def telemetry(self, seconds):
        rec = {"attitude": [], "position": [], "armed_state": []}
        t = self.drone.telemetry

        async def sub(gen, key):
            async for _ in gen:
                rec[key].append(time.time())
        tasks = [asyncio.create_task(sub(t.attitude_quaternion(), "attitude")),
                 asyncio.create_task(sub(t.position_velocity_ned(), "position")),
                 asyncio.create_task(sub(t.armed(), "armed_state"))]
        await asyncio.sleep(seconds)
        for x in tasks:
            x.cancel()
        return {k: arrival_stats(v) for k, v in rec.items()}

    def _odometry(self, mod):
        from mavsdk_grpc import mocap
        q = R_NED_FRD.as_quat()
        cov = mocap.Covariance([float("nan")])
        return mocap.Odometry(
            int(time.time() * 1e6), getattr(mocap.Odometry.MavFrame, os.environ.get("BENCH_FRAME", "LOCAL_FRD")),
            mocap.PositionBody(*[float(x) for x in POS_NED]), mocap.Quaternion(float(q[3]), float(q[0]), float(q[1]), float(q[2])),
            mocap.SpeedBody(*[float(x) for x in V_FRD]), mocap.AngularVelocityBody(*[float(x) for x in W_FRD]), cov, cov,
            0, mocap.Odometry.MavEstimatorType.VISION, 100)

    async def odom(self, seconds, rate):
        end, dt, sent = time.time() + seconds, 1.0 / rate, 0
        while time.time() < end:
            await self.mocap.set_odometry(self._odometry(None))
            sent += 1
            await asyncio.sleep(dt)
        return {"sent": sent}

    def _pos_cls(self):
        from mavsdk_grpc.offboard import PositionNedYaw
        return PositionNedYaw


# ---------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["mavros", "mavros_lean", "mavsdk", "mavsdk_grpc", "dds"])
    ap.add_argument("--phase", required=True, choices=["idle", "telemetry", "rtt", "odom", "offboard"])
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--rate", type=float, default=30.0)
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()

    cls = {"mavros": Mavros, "mavros_lean": MavrosLean, "dds": Dds, "mavsdk": MavsdkNative, "mavsdk_grpc": MavsdkGrpc}[a.method]
    m = cls()
    pids = m.start()
    result = {"method": a.method, "phase": a.phase, "expected": EXPECTED}
    is_async = a.method.startswith("mavsdk")

    async def run_async():
        result["connect_s"] = round(await m.connect(), 2)
        pids2 = m.bridge_pids() if hasattr(m, "bridge_pids") else pids
        result["startup_cpu_s"] = cpu_seconds(pids2) if pids2 else None
        await asyncio.sleep(WARMUP_S)
        sam = Sampler(pids2)
        sam.start()
        print("PHASE_START", flush=True)
        if a.phase == "idle":
            await asyncio.sleep(a.seconds)
        elif a.phase == "telemetry":
            result["streams"] = await m.telemetry(a.seconds)
        elif a.phase == "rtt":
            r = await m.rtt(a.n)
            result["rtt_ms"] = rtt_summary(r, a.n)
        elif a.phase == "odom":
            result.update(await m.odom(a.seconds, a.rate))
        elif a.phase == "offboard":
            result.update(await m.offboard(a.seconds, a.rate))
        result["resources"] = sam.summary()

    def run_sync():
        result["connect_s"] = round(m.wait_connected(), 2)
        result["startup_cpu_s"] = cpu_seconds(pids)
        time.sleep(WARMUP_S)
        sam = Sampler(pids)
        sam.start()
        print("PHASE_START", flush=True)
        if a.phase == "idle":
            time.sleep(a.seconds)
        elif a.phase == "telemetry":
            result["streams"] = m.telemetry(a.seconds)
        elif a.phase == "rtt":
            result["rtt_ms"] = rtt_summary(m.rtt(a.n), a.n)
        elif a.phase == "odom":
            result.update(m.odom(a.seconds, a.rate))
        elif a.phase == "offboard":
            result.update(m.offboard(a.seconds, a.rate))
        result["resources"] = sam.summary()

    try:
        if is_async:
            asyncio.run(run_async())
        else:
            run_sync()
    finally:
        if hasattr(m, "bridge"):
            kill(m.bridge)
    print(json.dumps(result))


def rtt_summary(r, n):
    if not r:
        return {"ok": 0, "of": n}
    ms = [x * 1e3 for x in r]
    return {"ok": len(r), "of": n, "p50": round(pct(ms, 50), 2), "p95": round(pct(ms, 95), 2), "p99": round(pct(ms, 99), 2),
            "max": round(max(ms), 2), "mean": round(statistics.fmean(ms), 2)}


if __name__ == "__main__":
    main()
