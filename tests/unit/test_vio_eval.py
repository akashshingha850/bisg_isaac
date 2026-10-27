"""VIO analysis + calibration tests, numpy only (no sim, ROS, GPU or containers): docs/vio.md.

    python3 -m unittest tests.unit.test_vio_eval -v              # from the repo root, any PC

Three parts:
  Synthetic   a flight built here with a known fault injected (latency, lever-arm error, yaw slip, frame gap + slip, tilted
              frame, no VIO): tests/vio_eval.py must recover each one, and must not invent faults in a clean flight.
  Archive     the 2026-10-15 sim flights (archive/vio-2026-10-15/*/topics.npz, the fields of the PX4 logs that vio_eval reads):
              re-analysed here, they must still show what docs/vio.md reports (the regression data for the calibration).
  Params      the calibrated values stay in docker/sim/px4/raptor.params, and vio_eval's camera lever arm stays
              equal to EKF2_EV_POS_* in raptor.params.
"""
import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tests"))
import vio_eval  # noqa: E402

ARCHIVE = os.path.join(ROOT, "archive", "vio-2026-10-15")
DEG = np.pi / 180


# ---- a synthetic flight --------------------------------------------------------------------------------------------
def yaw_quat(psi, pitch=0.0):
    """w, x, y, z of R = Rz(psi) Ry(pitch) (FRD body -> NED)."""
    cy, sy, cp, sp = np.cos(psi / 2), np.sin(psi / 2), np.cos(pitch / 2), np.sin(pitch / 2)
    return np.stack([cy * cp, -sy * sp, cy * sp, sy * cp], 1)


def flight(latency_s=0.0, lever_err=(0.0, 0.0, 0.0), yaw_slip_deg=0.0, gap=None, tilt_deg=0.0, ev=True, yaw_osc=False, seed=0):
    """A 60 s log as vio_eval reads it. Truth: rest 5 s, climb to 1 m, figure flown with yaw swings from 20 s.
    EV = the camera's pose/velocity in a frame turned 0.7 rad from NED, sampled at 30 Hz with the faults asked for:
    latency_s (EV shows the motion this late), lever_err (camera offset error, body FRD), yaw_slip_deg (EV yaw error after
    40 s), gap=(t_s, length_s, slip_m) (no EV samples, then the position off by slip_m in x), tilt_deg (EV frame pitched), yaw_osc (a 2.5 Hz, +-200 deg/s yaw-rate limit cycle from 30 s, the 2026-10-26 flight)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, 60.0, 0.01)
    z = -np.clip((t - 5) / 3, 0, 1) ** 2 * (3 - 2 * np.clip((t - 5) / 3, 0, 1))      # smooth climb to 1 m (NED up = -z)
    m = np.clip(t - 22, 0, None)                                       # hover 8-22 s, then a figure
    x, y = 0.8 * np.sin(0.3 * m), 0.8 * (1 - np.cos(0.25 * m))
    sstep = lambda u: np.clip(u, 0, 1) ** 2 * (3 - 2 * np.clip(u, 0, 1))
    psi = sum(np.pi / 2 * sstep((t - t0) / 1.5) for t0 in (9.0, 12.0, 15.0, 18.0))   # four 90 deg hover yaw steps (vio_bench)
    psi = psi + np.where(t > 22, 1.5 * np.sin(0.4 * (t - 22)), 0.0)                # then yaw swings in flight
    if yaw_osc:
        psi = psi + np.where(t > 30, 0.22 * np.sin(2 * np.pi * 2.5 * (t - 30)), 0.0)
    p = np.stack([x, y, z], 1)
    v = np.gradient(p, t, axis=0)
    w = np.stack([0 * t, 0 * t, np.gradient(psi, t)], 1)
    q = yaw_quat(psi)
    us = (t * 1e6 + 1e6).astype(np.int64)
    zeros = np.zeros_like(us)
    d = {"vehicle_local_position_groundtruth": {"timestamp": us, "timestamp_sample": zeros,
                                                **{k: p[:, i] for i, k in enumerate("xyz")},
                                                **{"v" + k: v[:, i] for i, k in enumerate("xyz")}},
         "vehicle_attitude_groundtruth": {"timestamp": us, "timestamp_sample": zeros,
                                          **{f"q[{i}]": q[:, i] for i in range(4)}},
         "vehicle_angular_velocity_groundtruth": {"timestamp": us, "timestamp_sample": zeros,
                                                  **{f"xyz[{i}]": w[:, i] for i in range(3)}},
         "vehicle_attitude": {"timestamp": us, "timestamp_sample": us, **{f"q[{i}]": q[:, i] for i in range(4)}},
         "vehicle_local_position": {"timestamp": us, "timestamp_sample": us, **{k: p[:, i] for i, k in enumerate("xyz")},
                                    "xy_valid": np.ones_like(us, dtype=np.uint8), "eph": np.full(len(t), 0.05)}}
    aid = {"timestamp": us[::4], "timestamp_sample": us[::4], "fused": np.ones(len(us[::4]), np.uint8),
           "innovation_rejected": np.zeros(len(us[::4]), np.uint8), "test_ratio[0]": np.full(len(us[::4]), 0.01),
           "innovation[0]": rng.normal(0, 0.01, len(us[::4])), "innovation_variance[0]": np.full(len(us[::4]), 0.01),
           "observation_variance[0]": np.full(len(us[::4]), 0.01)}
    d["estimator_aid_src_ev_pos"] = d["estimator_aid_src_ev_vel"] = d["estimator_aid_src_ev_yaw"] = aid
    if not ev:
        d["vehicle_local_position"]["x"] = d["vehicle_local_position"]["x"] + 0.01 * t   # drifts at rest, no EV
        d["estimator_status_flags"] = {"timestamp": us[::100], "cs_ev_pos": np.zeros(len(us[::100]), np.uint8),
                                       "cs_valid_fake_pos": np.ones(len(us[::100]), np.uint8)}
        return d

    te = np.arange(0.0, 60.0, 1 / 30)
    if gap:
        te = te[(te < gap[0]) | (te > gap[0] + gap[1])]
    ts = te - latency_s                                              # the motion each EV sample shows
    P = np.stack([np.interp(ts, t, p[:, k]) for k in range(3)], 1)
    V = np.stack([np.interp(ts, t, v[:, k]) for k in range(3)], 1)
    W = np.stack([np.interp(ts, t, w[:, k]) for k in range(3)], 1)
    ps = np.interp(ts, t, psi)
    R = vio_eval.rot(yaw_quat(ps))
    r = vio_eval.R_CAM_FRD + np.asarray(lever_err)
    cam = P + np.einsum("nij,j->ni", R, r)                           # camera position, NED
    vbody = np.einsum("nji,nj->ni", R, V) + np.cross(W, r)            # camera velocity, body FRD
    off = 0.7                                                       # EV frame heading vs NED
    pos_ev = cam @ vio_eval.rz(-off).T
    if gap:
        pos_ev[te > gap[0]] += np.array([gap[2], 0.0, 0.0])
    yaw_ev = ps - off + np.where(te > 40, yaw_slip_deg * DEG, 0.0)
    q_ev = yaw_quat(yaw_ev, tilt_deg * DEG)
    eus = (te * 1e6 + 1e6).astype(np.int64)
    n = len(te)
    d["vehicle_visual_odometry"] = {
        "timestamp": eus, "timestamp_sample": eus, **{f"position[{i}]": pos_ev[:, i] for i in range(3)},
        **{f"q[{i}]": q_ev[:, i] for i in range(4)}, **{f"velocity[{i}]": vbody[:, i] for i in range(3)},
        **{f"{k}_variance[0]": np.full(n, 1e-3) for k in ("position", "velocity", "orientation")},
        "pose_frame": np.full(n, 2), "velocity_frame": np.full(n, 3), "reset_counter": np.zeros(n)}
    return d


class Synthetic(unittest.TestCase):
    def run_eval(self, **kw):
        rep, fails, _ = vio_eval.analyse(flight(**kw))
        return rep, fails

    def test_clean_flight_has_no_faults(self):
        rep, fails = self.run_eval()
        self.assertEqual(fails, [])
        self.assertLessEqual(abs(rep["latency_ms"]["best_lag_ms"]), 5)
        for ax in "xy":
            self.assertAlmostEqual(rep["velocity_body"][ax]["scale"], 1.0, delta=0.01)
        self.assertLess(abs(rep["yaw"]["end_deg"]), 0.1)
        self.assertLess(rep["position"]["horiz_max_m"], 0.01)
        self.assertLess(max(abs(v) for v in rep["lever_arm_fit"]["delta_xy_m"]), 0.005)
        self.assertEqual(rep["frame_gaps"]["count"], 0)
        self.assertLess(rep["tilt"]["median_deg"], 0.1)
        self.assertGreater(len(rep["yaw_steps"]["steps"]), 0)

    def test_yaw_oscillation_is_found_and_commanded_turns_are_not(self):
        rep, fails = self.run_eval(yaw_osc=True)
        o = rep["yaw_oscillation"]
        self.assertTrue(o["detected"])
        self.assertAlmostEqual(o["first_t_s"], 30 - 6, delta=2)                 # t since takeoff (liftoff at ~6 s)
        self.assertGreater(o["peak_dps"], 150)
        self.assertTrue(any("yaw oscillation" in f for f in fails))
        self.assertEqual(rep["dominant_event"], "yaw oscillation (vehicle)")
        self.assertFalse(self.run_eval()[0]["yaw_oscillation"]["detected"])     # four 90 deg steps + 34 deg/s swings: not one

    def test_latency_is_measured_and_gated(self):
        rep, fails = self.run_eval(latency_s=0.06)
        self.assertAlmostEqual(rep["latency_ms"]["best_lag_ms"], 60, delta=5)
        self.assertTrue(any("latency" in f for f in fails))

    def test_lever_arm_error_is_recovered(self):
        rep, _ = self.run_eval(lever_err=(0.05, -0.03, 0.0))
        dx, dy = rep["lever_arm_fit"]["delta_xy_m"]
        self.assertAlmostEqual(dx, 0.05, delta=0.005)
        self.assertAlmostEqual(dy, -0.03, delta=0.005)

    def test_yaw_drift_is_not_taken_for_a_lever_arm(self):
        """A yaw error rotates positions about the takeoff point; the old whole-flight fit read that as a ~2 cm camera offset."""
        rep, _ = self.run_eval(yaw_slip_deg=-3.0)
        self.assertLess(max(abs(v) for v in rep["lever_arm_fit"]["delta_xy_m"]), 0.003)
        self.assertEqual(rep["lever_arm_fit"]["hover_rotations"], 4)

    def test_yaw_slip_is_measured(self):
        rep, _ = self.run_eval(yaw_slip_deg=-3.0)
        self.assertAlmostEqual(rep["yaw"]["end_deg"], -3.0, delta=0.1)

    def test_frame_gap_slip_is_found(self):
        rep, _ = self.run_eval(gap=(30.0, 0.4, 0.2))
        self.assertEqual(rep["frame_gaps"]["count"], 1)
        g = rep["frame_gaps"]["gaps"][0]
        self.assertAlmostEqual(g["gap_ms"], 433, delta=40)
        self.assertAlmostEqual(g["pos_err_change_m"], 0.2, delta=0.03)

    def test_tilted_ev_frame_is_found(self):
        rep, _ = self.run_eval(tilt_deg=4.0)
        self.assertAlmostEqual(rep["tilt"]["median_deg"], 4.0, delta=0.2)

    def test_log_without_vio_reports_arming_risk(self):
        rep, fails = self.run_eval(ev=False)
        self.assertFalse(rep["ev_present"])
        self.assertTrue(rep["no_vio"]["xy_valid_at_rest"])
        self.assertAlmostEqual(rep["no_vio"]["rest_drift_m"], 0.05, delta=0.01)
        self.assertTrue(any("no external vision" in f for f in fails))

    def test_ev_position_gate_only_when_ekf2_fuses_it_in_the_air(self):
        d = flight()
        d["estimator_aid_src_ev_pos"] = {**d["estimator_aid_src_ev_pos"],
                                         "fused": np.zeros_like(d["estimator_aid_src_ev_pos"]["fused"])}
        _, fails, _ = vio_eval.analyse(d)
        self.assertTrue(any("ev_pos fused" in f for f in fails))            # no flags: an unfused source is a fault
        us = d["vehicle_local_position"]["timestamp"]
        on_ground = (us < 4e6).astype(np.uint8)                              # enabled at boot, switched off before takeoff (EV_CTRL 12)
        d["estimator_status_flags"] = {"timestamp": us, "cs_ev_pos": on_ground, "cs_ev_vel": np.ones_like(on_ground)}
        rep, fails, _ = vio_eval.analyse(d)
        self.assertFalse(any("ev_pos fused" in f for f in fails))
        self.assertIn("not enabled", rep["ekf2"]["ev_pos"]["note"])

    def test_npz_extract_round_trip(self):
        d = flight(latency_s=0.02)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "topics.npz")
            vio_eval.save_npz(d, path)
            a, _, _ = vio_eval.analyse(d)
            b, _, _ = vio_eval.analyse(vio_eval.load(path))
        self.assertEqual(a, b)


def archived(run):
    path = os.path.join(ARCHIVE, run, "topics.npz")
    if not os.path.exists(path):
        raise unittest.SkipTest(f"{path} missing")
    return vio_eval.analyse(vio_eval.load(path))[:2]


class Archive(unittest.TestCase):
    """The 2026-10-15 flights (docs/vio.md, archive/vio-2026-10-15/README.md). Tolerances are loose on purpose: they guard
    the findings, not the last digit."""

    def test_pipeline_calibration_holds_in_every_flight(self):
        for run in ("1-baseline", "3-yawrate60-eva001-live", "4-confirm-fromfile"):
            with self.subTest(run=run):
                rep, _ = archived(run)
                self.assertLessEqual(abs(rep["latency_ms"]["best_lag_ms"]), 20)          # restamp_latency_ms 85 holds
                for ax in "xy":
                    self.assertAlmostEqual(rep["velocity_body"][ax]["scale"], 1.0, delta=0.02)
                self.assertLess(max(abs(v) for v in rep["lever_arm_fit"]["delta_xy_m"]), 0.02)   # EKF2_EV_POS_* right (hover steps)
                self.assertLess(max(rep["position"]["hf_noise_std_m"].values()), 0.015)  # 4-9 mm; run 4: 10 mm (slip step)

    def test_baseline_fast_yaw_slips_and_fails(self):
        rep, fails = archived("1-baseline")
        self.assertGreater(rep["yaw_steps"]["peak_rate_dps"], 300)
        self.assertGreater(rep["yaw_steps"]["worst_ev_err_added_deg"], 3.0)
        self.assertAlmostEqual(rep["yaw"]["end_deg"], -8.3, delta=0.5)
        self.assertLess(rep["yaw"]["ekf_end_deg"], rep["yaw"]["end_deg"])               # EKF2 heading lags (EVA 0.1)
        self.assertAlmostEqual(rep["ekf2"]["position_error"]["horiz_max_m"], 0.41, delta=0.03)
        self.assertTrue(any("EKF2 horizontal" in f for f in fails))

    def test_calibrated_yaw_rate_and_eva_pass(self):
        for run in ("3-yawrate60-eva001-live", "4-confirm-fromfile"):
            with self.subTest(run=run):
                rep, fails = archived(run)
                self.assertEqual(fails, [])
                self.assertLess(rep["yaw_steps"]["peak_rate_dps"], 120)
                self.assertLess(rep["yaw_steps"]["worst_ev_err_added_deg"], 1.5)
                self.assertLess(abs(rep["yaw"]["end_deg"] - rep["yaw"]["ekf_end_deg"]), 0.5)    # EKF2 follows the ZED

    def test_frame_gap_slips_and_tilts_the_sdk(self):
        rep, _ = archived("4-confirm-fromfile")
        worst = max(rep["frame_gaps"]["gaps"], key=lambda g: g["pos_err_change_m"])
        self.assertGreater(worst["gap_ms"], 350)
        self.assertGreater(worst["speed_mps"], 0.7)
        self.assertAlmostEqual(worst["pos_err_change_m"], 0.22, delta=0.03)
        self.assertLess(rep["tilt"]["start_deg"], 0.5)
        self.assertGreater(rep["tilt"]["end_deg"], 4.0)

    def test_tilt_persists_into_later_flights_of_the_sim_run(self):
        for run in ("5-vio-flight-gate", "6-smoke-after"):
            with self.subTest(run=run):
                rep, _ = archived(run)
                self.assertGreater(rep["tilt"]["start_deg"], 4.0)

    def test_no_vio_flight_was_still_armable(self):
        rep, fails = archived("2-no-vio-aborted")
        self.assertFalse(rep["ev_present"])
        nv = rep["no_vio"]
        self.assertTrue(nv["xy_valid_at_rest"])
        self.assertFalse(nv["ev_ever_fused"])
        self.assertTrue(nv["fake_pos_at_rest"])
        self.assertGreater(nv["rest_drift_m"], 0.5)


def read_params(name):
    out = {}
    with open(os.path.join(ROOT, "docker", "sim", "px4", f"{name}.params")) as fh:
        for line in fh:
            parts = line.split("#")[0].split()
            if len(parts) >= 3:
                out[parts[0]] = float(parts[1])
    return out


class Params(unittest.TestCase):
    def test_gps_denied_overlay_keeps_the_calibration(self):
        p = read_params("raptor")
        self.assertEqual(p["EKF2_EVA_NOISE"], 0.01)        # sqrt -> 0.1 rad effective (PX4 v1.17 yaw-variance quirk)
        self.assertEqual(p["MC_YAWRATE_MAX"], 60.0)
        self.assertEqual(p["EKF2_OF_QMIN_GND"], 1)
        self.assertEqual(p["EKF2_EV_CTRL"], 12)            # 3D vel + yaw (the Manhattan compass holds the yaw), not position / the drifting z
        self.assertEqual(p["EKF2_EV_DELAY"], 0)            # the bridge stamps at capture

    def test_camera_mount_is_one_value_in_three_files(self):
        """Twin mount (raptor.yaml, FLU), EKF2 lever arm (raptor.params, FRD) and the wrapper's initial_base_pose (zed.yaml, FLU)
        are one physical fact; vio_eval reads raptor.params. Real drone: centred, forward offset only (y = 0)."""
        import yaml
        p = read_params("raptor")
        frd = [p["EKF2_EV_POS_X"], p["EKF2_EV_POS_Y"], p["EKF2_EV_POS_Z"]]
        self.assertEqual(frd, list(vio_eval.R_CAM_FRD))
        with open(os.path.join(ROOT, "docker", "sim", "assets", "vehicles", "raptor", "raptor.yaml")) as fh:
            twin = yaml.safe_load(fh)["vehicles"][0]["sensors"]["zed"]["mount_xyz_rpy"]
        with open(os.path.join(ROOT, "docker", "zed", "zed.yaml")) as fh:
            base = yaml.safe_load(fh)["positional_tracking"]["initial_base_pose"]
        flu_from_frd = [frd[0], -frd[1], -frd[2]]
        for name, flu in (("raptor.yaml sensors.zed.mount_xyz_rpy", twin), ("zed.yaml initial_base_pose", base)):
            for a, b in zip(flu[:3], flu_from_frd):
                self.assertAlmostEqual(a, b, places=6, msg=f"{name} {flu[:3]} != EKF2_EV_POS (FLU) {flu_from_frd}")
            self.assertEqual(list(flu[3:6]), [0, 0, 0], msg=name)
        self.assertEqual(frd[1], 0.0)                                   # centred on the real drone


if __name__ == "__main__":
    unittest.main()
