#!/usr/bin/env python3
"""
Phase 3 exit test (docs/roadmap.md): GPS-denied flight on mock VIO.

OFFBOARD takeoff -> hold -> square -> OFFBOARD descent, all over the contract's ROS path
(mavros/setpoint_position/local, mavros/set_mode, mavros/cmd/arming), comparing
mavros/local_position/pose against Pegasus ground truth (state/pose) the whole time.
PASS = every sample within --tol (default 0.3 m, the roadmap's bound) in x, y and z,
the square completed and the vehicle landed and disarmed.

Why OFFBOARD throughout: MAVROS sends vision odometry in MAV_FRAME_LOCAL_FRD (arbitrary
heading, like a real ZED's odom frame), so EKF2 never aligns yaw to north and never publishes a
global position. Hold/Takeoff/RTL refuse to engage without one, and AUTO.LAND engages (its mode
requirement is local position only) but navigator plans the landing point in lat/lon: on
2026-09-25 it flew the drone off at ~6 m/s towards lat/lon 0,0 and into a wall. So the test lands
with a velocity setpoint in OFFBOARD (mavros/setpoint_raw/local, 0.5 m/s down), waits for the
land detector (mavros/extended_state ON_GROUND) and disarms through mavros/cmd/arming. It must
be a velocity setpoint: PX4's land detector only accepts ground contact while a descent velocity
is commanded (MulticopterLandDetector, trajectory_setpoint.velocity[2] >= 1.1 * LNDMC_Z_VEL_MAX);
a position setpoint below the ground just sits there, armed. `--land auto` keeps the AUTO.LAND path for reproducing the fly-away.

Needs the GPS-denied scenario and the ZED stack feeding PX4 (`./bisg zed up`, zed.yaml odometry.enabled):
    SIM_SCENARIO=single_iris_vio ./bisg all headless
    docker exec bisg-ros python3 /workspace/tests/vio_flight.py --drone 1
Reading ground truth is test-only; vehicle nodes must not (parity rule, plan.md §8).
Exit code 0 = PASS. --csv writes every sample for plotting.
"""
import argparse
import csv
import math
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import ExtendedState, PositionTarget, State
from mavros_msgs.srv import CommandBool, CommandLong, SetMode
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data


class Abort(Exception):
    pass


class Flight:
    def __init__(self, drone, tol, csv_path):
        ns = f"/drone_{drone}"
        # Sim time like every node in the sim stack (interface-contract.md, /clock).
        self.node = rclpy.create_node("vio_flight_test", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.tol = tol
        self.truth = self.est = None
        self.truth0 = self.est0 = None
        self.state = State()
        self.ext = ExtendedState()
        self.max_err = [0.0, 0.0, 0.0]
        self.samples = 0
        self.phase = "init"
        self.sp = PoseStamped()
        self.sp.header.frame_id = "map"
        self.sp.pose.orientation.w = 1.0
        self.streaming = False
        self.abort_reason = None
        self.writer = None
        if csv_path:
            self.csv_file = open(csv_path, "w", newline="")
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(["t", "phase", "armed", "mode", "truth_x", "truth_y", "truth_z",
                                  "est_x", "est_y", "est_z", "err_x", "err_y", "err_z"])
        self.t0 = time.time()
        n = self.node
        n.create_subscription(PoseStamped, f"{ns}/state/pose", self._on_truth, qos_profile_sensor_data)
        n.create_subscription(PoseStamped, f"{ns}/mavros/local_position/pose", self._on_est, qos_profile_sensor_data)
        n.create_subscription(State, f"{ns}/mavros/state", self._on_state, 10)
        n.create_subscription(ExtendedState, f"{ns}/mavros/extended_state", self._on_ext, 10)
        self.pub_sp = n.create_publisher(PoseStamped, f"{ns}/mavros/setpoint_position/local", 10)
        self.pub_raw = n.create_publisher(PositionTarget, f"{ns}/mavros/setpoint_raw/local", 10)
        self.descend = None  # m/s down; when set, stream a velocity setpoint instead of self.sp
        self.cli_mode = n.create_client(SetMode, f"{ns}/mavros/set_mode")
        self.cli_arm = n.create_client(CommandBool, f"{ns}/mavros/cmd/arming")
        self.cli_cmd = n.create_client(CommandLong, f"{ns}/mavros/cmd/command")
        n.create_timer(0.05, self._stream)  # 20 Hz sim time; PX4 needs > 2 Hz to stay in OFFBOARD

    # --- callbacks -----------------------------------------------------------------------------
    def _on_truth(self, m):
        self.truth = (m.pose.position.x, m.pose.position.y, m.pose.position.z)

    def _on_state(self, m):
        self.state = m

    def _on_ext(self, m):
        self.ext = m

    def _on_est(self, m):
        self.est = (m.pose.position.x, m.pose.position.y, m.pose.position.z)
        if self.truth is None or self.truth0 is None:
            return
        # Compare displacements from the pre-flight pose: the EKF local origin is where EV
        # fusion started, not necessarily the sim world origin.
        err = [(self.est[i] - self.est0[i]) - (self.truth[i] - self.truth0[i]) for i in range(3)]
        if self.state.armed:
            self.max_err = [max(a, abs(b)) for a, b in zip(self.max_err, err)]
            self.samples += 1
        if self.writer:
            self.writer.writerow([f"{time.time() - self.t0:.2f}", self.phase, int(self.state.armed), self.state.mode,
                                  *(f"{v:.3f}" for v in self.truth), *(f"{v:.3f}" for v in self.est),
                                  *(f"{v:.3f}" for v in err)])
        if self.state.armed and not self.abort_reason and (
                max(abs(e) for e in err) > 3 * self.tol or self.truth[2] - self.truth0[2] > 8.0):
            self.abort_reason = f"estimate off ground truth by {[round(e, 2) for e in err]} m, truth={self.truth}"


    def _stream(self):
        if not self.streaming:
            return
        if self.descend is not None:
            t = PositionTarget()
            t.header.stamp = self.node.get_clock().now().to_msg()
            t.coordinate_frame = PositionTarget.FRAME_LOCAL_NED  # MAVROS takes ENU values and converts
            t.type_mask = (PositionTarget.IGNORE_PX | PositionTarget.IGNORE_PY | PositionTarget.IGNORE_PZ
                           | PositionTarget.IGNORE_AFX | PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ
                           | PositionTarget.IGNORE_YAW_RATE)
            t.velocity.z = -self.descend
            self.pub_raw.publish(t)
        else:
            self.sp.header.stamp = self.node.get_clock().now().to_msg()
            self.pub_sp.publish(self.sp)

    # --- helpers -------------------------------------------------------------------------------
    def spin(self):
        rclpy.spin_once(self.node, timeout_sec=0.05)
        if self.abort_reason:  # raised here, not in the callback: can't call a service from inside spin
            raise Abort(self.abort_reason)

    def spin_for(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.spin()

    def wait_for(self, cond, timeout, what):
        end = time.time() + timeout
        while time.time() < end:
            self.spin()
            if cond():
                return True
        print(f"[vio_flight] TIMEOUT waiting for {what}", flush=True)
        return False

    def call(self, cli, req, timeout=10.0):
        if not cli.wait_for_service(timeout_sec=timeout):
            return None
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(self.node, fut, timeout_sec=timeout)
        return fut.result()

    def set_mode(self, mode):
        r = self.call(self.cli_mode, SetMode.Request(custom_mode=mode))
        ok = self.wait_for(lambda: self.state.mode == mode, 10, f"mode {mode}")
        print(f"[vio_flight] mode {mode}: {'ok' if ok else 'REFUSED'} (sent={getattr(r, 'mode_sent', None)})", flush=True)
        return ok

    def kill(self, why):
        print(f"[vio_flight] ABORT: {why} — force disarm", flush=True)
        # MAV_CMD_COMPONENT_ARM_DISARM, param2 21196 = force (sim only: the drone drops)
        self.call(self.cli_cmd, CommandLong.Request(command=400, param1=0.0, param2=21196.0), timeout=2.0)

    def goto(self, dx, dy, alt, settle, phase):
        """Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds."""
        self.phase = phase
        self.sp.pose.position.x = self.est0[0] + dx
        self.sp.pose.position.y = self.est0[1] + dy
        self.sp.pose.position.z = self.est0[2] + alt

        def there():
            return self.est and math.dist(self.est, (self.sp.pose.position.x, self.sp.pose.position.y,
                                                     self.sp.pose.position.z)) < 0.25
        if not self.wait_for(there, 40, f"{phase} setpoint"):
            return False
        self.spin_for(settle)
        err = [round(e, 3) for e in self.max_err]
        print(f"[vio_flight] {phase:8s} reached est={[round(v, 2) for v in self.est]} "
              f"truth={[round(v, 2) for v in self.truth]} max|err| so far xyz={err}", flush=True)
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--side", type=float, default=3.0, help="square side, metres")
    ap.add_argument("--hold", type=float, default=10.0, help="hover seconds after takeoff")
    ap.add_argument("--tol", type=float, default=0.3, help="max |estimate - truth| per axis, metres")
    ap.add_argument("--land", choices=["offboard", "auto"], default="offboard",
                    help="offboard = descend in OFFBOARD (default); auto = AUTO.LAND (unsafe GPS-denied, see docstring)")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()

    rclpy.init()
    f = Flight(a.drone, a.tol, a.csv)
    ok = False
    try:
        if not f.wait_for(lambda: f.truth and f.est and f.state.connected, 60,
                          "ground truth + local_position + MAVROS connected"):
            return 2
        f.spin_for(2.0)
        f.truth0, f.est0 = f.truth, f.est
        print(f"[vio_flight] start est={[round(v, 2) for v in f.est0]} truth={[round(v, 2) for v in f.truth0]}",
              flush=True)

        # Setpoints must already be flowing before PX4 accepts OFFBOARD.
        f.sp.pose.position.x, f.sp.pose.position.y, f.sp.pose.position.z = f.est0[0], f.est0[1], f.est0[2] + a.alt
        f.streaming = True
        f.spin_for(2.0)
        if not f.set_mode("OFFBOARD"):
            return 3
        r = f.call(f.cli_arm, CommandBool.Request(value=True))
        if not (r and r.success) or not f.wait_for(lambda: f.state.armed, 10, "armed"):
            print("[vio_flight] arming refused (./bisg debug px4 commander check)", flush=True)
            return 3
        print("[vio_flight] armed in OFFBOARD", flush=True)

        s = a.side
        steps = [(0, 0, a.hold, "takeoff"), (s, 0, 2, "square-1"), (s, s, 2, "square-2"),
                 (0, s, 2, "square-3"), (0, 0, 2, "square-4")]
        for dx, dy, settle, phase in steps:
            if not f.goto(dx, dy, a.alt, settle, phase):
                return 4

        f.phase = "land"
        if a.land == "auto":
            if not f.set_mode("AUTO.LAND"):
                return 5
            f.streaming = False
        else:
            f.descend = 0.5  # see module docstring: the land detector needs a commanded descent velocity
            if not f.wait_for(lambda: f.ext.landed_state == ExtendedState.LANDED_STATE_ON_GROUND, 60,
                              "land detector ON_GROUND"):
                return 5
            f.call(f.cli_arm, CommandBool.Request(value=False))
            f.streaming = False
        if not f.wait_for(lambda: not f.state.armed, 90, "disarmed after landing"):
            return 5
        f.spin_for(1.0)
        worst = max(f.max_err)
        ok = worst <= a.tol
        print(f"[vio_flight] landed and disarmed. max|est - truth| x={f.max_err[0]:.3f} y={f.max_err[1]:.3f} "
              f"z={f.max_err[2]:.3f} m over {f.samples} airborne samples (tol {a.tol} m) — "
              f"{'PASS' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 6
    except Abort as exc:
        f.kill(str(exc))
        return 10
    finally:
        if f.writer:
            f.csv_file.close()
        f.node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    sys.exit(main())
