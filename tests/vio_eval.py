#!/usr/bin/env python3
"""
ZED VIO accuracy + EKF2 fusion against ground truth, from the PX4 log of a tests/vio_bench.py flight (docs/vio.md).
numpy only (matplotlib optional, for --plot): runs on the host or in any container, no sim needed.

Inputs, all on PX4's clock (no cross-clock alignment): `vehicle_visual_odometry` = the ZED odometry exactly as EKF2 received it
(zed-bridge restamp -> MAVROS odometry/out -> ODOMETRY), the twin's `vehicle_*_groundtruth` (`sensors.ground_truth`), EKF2's
`estimator_aid_src_*`, `vehicle_local_position`, `vehicle_attitude` and `estimator_status_flags`.

What it measures (airborne samples only):
  latency    best shift of the EV velocity against ground truth (+-300 ms). The EV stamp should already be the capture time
             (zed.yaml sim: restamp_latency_ms), so the best lag should be ~0; a residual goes into restamp_latency_ms.
  velocity   EV body velocity vs the true velocity of the camera (body + w x r_cam): scale (LS slope), bias, RMSE per axis
             -> EKF2_EVV_NOISE. Velocity frame and sign errors show up here as a slope far from 1.
  yaw        EV yaw (after removing the constant start offset: the EV frame has an arbitrary heading) vs true yaw: drift
             -> EKF2_EVA_NOISE (PX4 v1.17 quirk: the yaw floor is max(var, EVA_NOISE), so effective std = sqrt(EVA_NOISE)).
  yaw_steps  per rotation (|yaw rate| > 0.3 rad/s): angle, peak rate, yaw error the ZED and EKF2 kept afterwards (-> MC_YAWRATE_MAX).
  position   EV body position (camera minus R*r_cam) in the start-aligned frame vs ground truth, as displacements from takeoff:
             drift over time and per metre flown, plus the short-term noise (residual after a 2 s moving average) -> EKF2_EVP_NOISE.
  lever arm  the yaw-correlated part of the position error: fits the camera offset that best explains it (vs EKF2_EV_POS_*).
  gaps       EV samples missing > 150 ms in the air, with the speed and the position error they left behind (SDK slip).
  tilt       EV roll/pitch vs truth: the sim SDK has no IMU, so a tilt of its world frame is not corrected (climbs leak sideways).
  EKF2       fused fraction and test ratios of each aid source, and the EKF2 position error vs ground truth.
  no_vio     (a log without EV) whether EKF2 still called the position valid at rest, and how far it drifted (arming without VIO).

    python3 tests/vio_eval.py --ulog <flight.ulg> --out <report dir> [--plot] [--save-npz <dir>/topics.npz]
    python3 tests/vio_eval.py --npz archive/vio-2026-10-15/<run>/topics.npz --out /tmp/r [--series]
Exit 0 = every gate passes (GATES below; they judge the sim pipeline, not a real ZED). The analysis is `analyse(load(path))`
(tests/unit/test_vio_eval.py); `--save-npz` keeps only the fields read here (~1/30 of the .ulg) for archive/vio-*/.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ulog_lite  # noqa: E402
from range_flow_eval import interp, quat_interp, rot, slope, stats  # noqa: E402

AID = ["timestamp", "timestamp_sample", "observation", "observation_variance", "innovation", "innovation_variance",
       "test_ratio", "fused", "innovation_rejected"]
# topic -> fields read here (a field `f` is kept when it is listed or is an element `f[i]` of a listed array)
KEEP = {
    "vehicle_visual_odometry": ["timestamp", "timestamp_sample", "position", "q", "velocity", "position_variance",
                                "velocity_variance", "orientation_variance", "pose_frame", "velocity_frame", "reset_counter"],
    "vehicle_local_position": ["timestamp", "timestamp_sample", "x", "y", "z", "vx", "vy", "vz", "xy_valid", "eph", "dist_bottom"],
    "vehicle_local_position_groundtruth": ["timestamp", "timestamp_sample", "x", "y", "z", "vx", "vy", "vz"],
    "vehicle_attitude_groundtruth": ["timestamp", "timestamp_sample", "q"],
    "vehicle_angular_velocity_groundtruth": ["timestamp", "timestamp_sample", "xyz"],
    "vehicle_attitude": ["timestamp", "timestamp_sample", "q"],
    "estimator_aid_src_ev_pos": AID, "estimator_aid_src_ev_vel": AID, "estimator_aid_src_ev_yaw": AID,
    "estimator_aid_src_optical_flow": AID, "estimator_aid_src_baro_hgt": AID, "estimator_aid_src_rng_hgt": AID,
    "estimator_status_flags": ["timestamp", "cs_*"],
    "distance_sensor": ["timestamp", "current_distance"],
}
TOPICS = list(KEEP)
R_CAM_FRD = np.array([0.1205, 0.0011, -0.0527])      # EKF2_EV_POS_X/Y/Z (docker/sim/px4/raptor.params)
GAP_MS = 150.0                                         # an EV gap longer than this is reported
GATES = {
    "latency_abs_ms": 30.0,          # residual EV latency after the bridge's restamp
    "vel_scale_err": 0.05,           # |slope - 1| per horizontal axis
    "ekf_horiz_max_m": 0.30,         # Phase 3 bound (tests/vio_flight.py)
    "ev_pos_fused_min": 0.90,        # fraction of airborne EV samples fused
    "ev_vel_fused_min": 0.90,
}


# ---- I/O -----------------------------------------------------------------------------------------------------------
def _kept(field, names):
    return any(field == n or field.startswith(n + "[") or (n.endswith("*") and field.startswith(n[:-1])) for n in names)


def load(path):
    """{topic: {field: array}} from a PX4 .ulg or from a --save-npz extract."""
    if path.endswith(".npz"):
        d = {}
        with np.load(path, allow_pickle=False) as z:
            for key in z.files:
                topic, field = key.split("|", 1)
                d.setdefault(topic, {})[field] = z[key]
        return d
    return ulog_lite.read(path, TOPICS)


def save_npz(d, path):
    arrays = {f"{t}|{f}": v for t, fields in d.items() if t in KEEP for f, v in fields.items() if _kept(f, KEEP[t])}
    np.savez_compressed(path, **arrays)


# ---- helpers -------------------------------------------------------------------------------------------------------
def yaw_of(q):
    w, x, y, z = q.T
    return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def roll_pitch(q):
    w, x, y, z = q.T
    return np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)), np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))


def tstamp(topic):
    """timestamp_sample when the publisher sets it, else timestamp (the *_groundtruth topics leave it 0)."""
    ts = topic.get("timestamp_sample")
    if ts is not None and np.all(ts > 0):
        return ts.astype(float)
    return topic["timestamp"].astype(float)


def continuous(q):
    """Flip quaternion signs so neighbours agree (q and -q are one rotation), as linear interpolation needs."""
    s = np.sign(np.sum(q[1:] * q[:-1], 1))
    s[s == 0] = 1
    return q * np.concatenate([[1.0], np.cumprod(s)])[:, None]


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def rz(psi):
    c, s = np.cos(psi), np.sin(psi)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def vec(topic, name, n):
    return np.stack([topic[f"{name}[{i}]"] for i in range(n)], 1).astype(float)


def cols(topic, name):
    """[N, k] of a scalar field `name` or the elements of the array field `name[i]`."""
    if name in topic:
        return topic[name].astype(float)[:, None]
    return np.stack([topic[c] for c in sorted(c for c in topic if c.startswith(name + "["))], 1).astype(float)


# ---- analysis ------------------------------------------------------------------------------------------------------
class Truth:
    def __init__(self, d):
        lp, att, av = (d["vehicle_local_position_groundtruth"], d["vehicle_attitude_groundtruth"],
                       d["vehicle_angular_velocity_groundtruth"])
        self.t = tstamp(lp)
        self.p = np.stack([lp["x"], lp["y"], lp["z"]], 1).astype(float)
        self.v = np.stack([lp["vx"], lp["vy"], lp["vz"]], 1).astype(float)
        self.t_att, self.q = tstamp(att), continuous(vec(att, "q", 4))
        self.t_av, self.w = tstamp(av), vec(av, "xyz", 3)
        self.z_rest = float(np.median(self.p[: max(10, len(self.p) // 50), 2]))

    def at(self, t, lag=0.0):
        tt = t - lag
        q = np.stack([interp(self.t_att, self.q[:, k], tt) for k in range(4)], 1)
        q /= np.linalg.norm(q, axis=1, keepdims=True)
        return (np.stack([interp(self.t, self.p[:, k], tt) for k in range(3)], 1), q,
                np.stack([interp(self.t, self.v[:, k], tt) for k in range(3)], 1),
                np.stack([interp(self.t_av, self.w[:, k], tt) for k in range(3)], 1))


def ekf_section(d, gt, air_margin):
    ekf = {}
    for src in ("ev_pos", "ev_vel", "ev_yaw", "optical_flow", "baro_hgt", "rng_hgt"):
        s = d.get(f"estimator_aid_src_{src}")
        if s is None or len(s["timestamp"]) == 0:
            continue
        ts = tstamp(s)
        m = interp(gt.t, gt.p[:, 2], ts) < gt.z_rest - air_margin
        if not m.any():
            continue
        tr = np.max(cols(s, "test_ratio"), 1)[m]
        ekf[src] = {"n": int(m.sum()), "fused": float(np.mean(s["fused"][m])),
                    "rejected": float(np.mean(s["innovation_rejected"][m])),
                    "test_ratio_p50": float(np.percentile(tr, 50)), "test_ratio_p95": float(np.percentile(tr, 95)),
                    "innov_std": [float(v) for v in np.std(cols(s, "innovation")[m], 0)],
                    "innov_std_expected": [float(v) for v in np.sqrt(np.median(cols(s, "innovation_variance")[m], 0))],
                    "obs_std_used": [float(v) for v in np.sqrt(np.median(cols(s, "observation_variance")[m], 0))]}
    lpe = d["vehicle_local_position"]
    te = tstamp(lpe)
    pe = np.stack([lpe["x"], lpe["y"], lpe["z"]], 1).astype(float)
    pgt = np.stack([interp(gt.t, gt.p[:, k], te) for k in range(3)], 1)
    me = (pgt[:, 2] < gt.z_rest - air_margin) & np.all(np.isfinite(pgt), 1)
    j0 = int(np.argmax(me))
    ee = (pe - pe[j0]) - (pgt - pgt[j0])
    he = np.linalg.norm(ee[:, :2], axis=1)
    ekf["position_error"] = {"x": stats(ee[me, 0]), "y": stats(ee[me, 1]), "z": stats(ee[me, 2]),
                             "horiz_max_m": float(np.nanmax(he[me])), "horiz_end_m": float(he[me][-1])}
    return ekf, {"te": te, "j0": j0, "me": me, "ee": ee}


def no_vio_section(d, gt, air_margin):
    """A log without EV: did EKF2 still report a valid horizontal position at rest (-> PX4 arms in OFFBOARD), and drift?"""
    lpe = d["vehicle_local_position"]
    te = tstamp(lpe)
    zg = interp(gt.t, gt.p[:, 2], te)
    rest = np.isfinite(zg) & (te < te[np.argmax(zg < gt.z_rest - air_margin)])
    valid = rest & (lpe["xy_valid"] > 0)
    out = {"xy_valid_at_rest": bool(valid.any()), "xy_valid_at_rest_s": float(valid.sum() * np.median(np.diff(te)) / 1e6)}
    if valid.any():
        xy = np.stack([lpe["x"], lpe["y"]], 1).astype(float)[valid]
        out["rest_drift_m"] = float(np.max(np.linalg.norm(xy - xy[0], axis=1)))
        out["eph_at_takeoff_m"] = float(lpe["eph"][valid][-1])
    f = d.get("estimator_status_flags")
    if f is not None:
        out["ev_ever_fused"] = bool(any(np.any(f[k]) for k in ("cs_ev_pos", "cs_ev_vel", "cs_ev_yaw") if k in f))
        out["fake_pos_at_rest"] = bool(np.any(f.get("cs_valid_fake_pos", np.zeros(1))))
    return out


def analyse(d, air_margin=0.15):
    """-> (report dict, list of failed gates, series for plot())."""
    rep, fails = {}, []
    gt = Truth(d)
    ekf, ser_e = ekf_section(d, gt, air_margin)
    ev = d.get("vehicle_visual_odometry")
    rep["ev_present"] = ev is not None and len(ev["timestamp"]) > 0
    if not rep["ev_present"]:
        rep["no_vio"] = no_vio_section(d, gt, air_margin)
        rep["ekf2"] = ekf
        fails.append("no external vision (vehicle_visual_odometry) in the log")
        rep["gates"], rep["fails"] = GATES, fails
        return rep, fails, None

    # ---- external vision as EKF2 received it --------------------------------------------------------------------
    t_ev = ev["timestamp_sample"].astype(float)
    p_ev, q_ev, v_ev = vec(ev, "position", 3), vec(ev, "q", 4), vec(ev, "velocity", 3)
    rep["ev_frames"] = {"pose_frame": int(np.median(ev["pose_frame"])), "velocity_frame": int(np.median(ev["velocity_frame"])),
                        "reset_counter_changes": int(np.count_nonzero(np.diff(ev["reset_counter"].astype(int)))),
                        "rate_hz": float(1e6 / np.median(np.diff(t_ev))),
                        "gap_max_s": float(np.diff(t_ev).max() / 1e6),
                        "reported_var_median": {k: float(np.median(ev[f"{k}_variance[0]"]))
                                                for k in ("position", "velocity", "orientation")}}
    pg, qg, vg, wg = gt.at(t_ev)
    air = (pg[:, 2] < gt.z_rest - air_margin) & np.all(np.isfinite(pg), 1)
    if air.sum() < 50:
        raise ValueError("not enough airborne EV samples")
    i0 = int(np.argmax(air))                                   # first airborne EV sample
    rep["airborne_s"] = float((t_ev[air][-1] - t_ev[air][0]) / 1e6)

    # ---- latency (velocity cross-check, body frame) -----------------------------------------------------------------
    def v_cam_body(lag):
        _, q, v, w = gt.at(t_ev, lag)
        Rt = np.transpose(rot(q), (0, 2, 1))
        return np.einsum("nij,nj->ni", Rt, v) + np.cross(w, R_CAM_FRD)

    lags = np.arange(-0.3, 0.3001, 0.005) * 1e6
    rms = []
    for lag in lags:
        e = (v_ev - v_cam_body(lag))[air, :2]
        e = e[np.all(np.isfinite(e), 1)]
        rms.append(np.sqrt(np.mean(e ** 2)))
    best = float(lags[int(np.argmin(rms))] / 1e3)
    rep["latency_ms"] = {"best_lag_ms": best, "rmse_at_0": float(rms[len(lags) // 2]), "rmse_at_best": float(min(rms)),
                         "note": "positive = the EV sample shows the motion this much after its stamp (stamp too early)"}
    if abs(best) > GATES["latency_abs_ms"]:
        fails.append(f"EV latency {best:+.0f} ms")

    # ---- velocity -------------------------------------------------------------------------------------------------
    vc = v_cam_body(0.0)
    vel = {}
    for k, ax in enumerate("xyz"):
        e = (v_ev[:, k] - vc[:, k])[air]
        k_s, corr = slope(v_ev[air, k], vc[air, k])
        vel[ax] = {**stats(e), "scale": k_s, "corr": corr}
        if ax != "z" and abs(k_s - 1) > GATES["vel_scale_err"]:
            fails.append(f"EV velocity {ax} scale {k_s:.3f}")
    rep["velocity_body"] = vel

    # ---- yaw ------------------------------------------------------------------------------------------------------
    y_ev, y_gt = yaw_of(q_ev), yaw_of(qg)
    off = wrap(y_gt[i0] - y_ev[i0])
    yerr = wrap(y_ev + off - y_gt)
    rot_total = float(np.nansum(np.abs(wrap(np.diff(y_gt[air])))))
    rep["yaw"] = {**{k: float(np.degrees(v)) if k != "n" else v for k, v in stats(yerr[air]).items()},
                  "unit": "deg", "end_deg": float(np.degrees(yerr[air][-1])), "rotated_total_deg": float(np.degrees(rot_total)),
                  "drift_deg_per_rev": float(np.degrees(yerr[air][-1] - yerr[i0]) / max(rot_total / (2 * np.pi), 1e-3))}

    # ---- yaw steps: what each rotation cost the ZED and EKF2 -------------------------------------------------------
    yerr_k = None
    if "vehicle_attitude" in d:
        ka = d["vehicle_attitude"]
        y_k = yaw_of(quat_interp(tstamp(ka), vec(ka, "q", 4), t_ev))
        yerr_k = wrap(y_k + wrap(y_gt[i0] - y_k[i0]) - y_gt)
    spinning = np.abs(wg[:, 2]) > 0.3
    steps = []
    edges = np.flatnonzero(np.diff(spinning.astype(int)))
    for s in edges[~spinning[edges]] + 1:                      # rising edges
        ends = edges[(edges >= s) & spinning[edges]] + 1
        if not len(ends):
            continue
        e = ends[0]
        if (t_ev[e] - t_ev[s]) < 0.3e6 or not (air[max(0, s - 40)] and air[min(len(air) - 1, e + 60)]):
            continue
        pre, post = slice(max(0, s - 40), s - 5), slice(e + 20, min(len(t_ev), e + 60))
        row = {"t_s": float((t_ev[s] - t_ev[i0]) / 1e6),
               "rotated_deg": float(np.degrees(np.nansum(wg[s:e, 2] * np.diff(t_ev[s:e + 1]) / 1e6))),
               "peak_rate_dps": float(np.degrees(np.nanmax(np.abs(wg[s:e, 2])))),
               "ev_err_added_deg": float(np.degrees(np.median(yerr[post]) - np.median(yerr[pre])))}
        if yerr_k is not None:
            row["ekf_err_after_deg"] = float(np.degrees(np.median(yerr_k[post])))
        steps.append(row)
    rep["yaw_steps"] = {"steps": steps,
                        "peak_rate_dps": max((r["peak_rate_dps"] for r in steps), default=0.0),
                        "worst_ev_err_added_deg": max((abs(r["ev_err_added_deg"]) for r in steps), default=0.0)}
    if yerr_k is not None:
        rep["yaw"]["ekf_end_deg"] = float(np.degrees(np.median(yerr_k[air][-100:])))

    # ---- position -------------------------------------------------------------------------------------------------
    R0 = rz(off)                                                # EV local frame -> NED (heading offset at takeoff)
    pb_ev = p_ev - np.einsum("nij,j->ni", rot(q_ev), R_CAM_FRD)  # camera -> body origin, in the EV frame
    pb_ned = pb_ev @ R0.T
    disp_ev = pb_ned - pb_ned[i0]
    disp_gt = pg - pg[i0]
    perr = disp_ev - disp_gt
    path = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pg[:, :2], axis=0), axis=1))])
    path -= path[i0]
    h = np.linalg.norm(perr[:, :2], axis=1)
    rep["position"] = {"x": stats(perr[air, 0]), "y": stats(perr[air, 1]), "z": stats(perr[air, 2]),
                       "horiz_end_m": float(h[air][-1]), "horiz_max_m": float(np.nanmax(h[air])),
                       "path_m": float(path[air][-1]), "drift_pct_of_path": float(100 * h[air][-1] / max(path[air][-1], 1e-3))}
    n = max(3, int(round(2.0 * rep["ev_frames"]["rate_hz"])))   # short-term noise: residual after a ~2 s moving average
    ker = np.ones(n) / n
    noise = {}
    for k, ax in enumerate("xy"):
        e = perr[:, k].copy()
        e[~air] = np.nan
        ok = np.isfinite(e)
        sm = np.convolve(np.where(ok, e, 0), ker, "same") / np.maximum(np.convolve(ok.astype(float), ker, "same"), 1e-9)
        noise[ax] = float(np.std((e - sm)[ok]))
    rep["position"]["hf_noise_std_m"] = noise

    # ---- lever arm: does the error follow the yaw? (a wrong r_cam gives err = (R(yaw) - R(yaw0)) * dr) ---------------
    Rg = rot(qg)
    A = (Rg - Rg[i0])[air][:, :2, :2].reshape(-1, 2)            # horizontal part only
    b = perr[air, :2].reshape(-1)
    ok = np.isfinite(b) & np.all(np.isfinite(A), 1)
    dr, *_ = np.linalg.lstsq(A[ok], b[ok], rcond=None)
    rep["lever_arm_fit"] = {"delta_xy_m": [float(v) for v in dr],
                            "note": "camera offset error that best explains the yaw-correlated position error; ~0 = EKF2_EV_POS ok"}

    # ---- frame gaps: the sim SDK has no IMU to bridge them, so a gap while moving slips the pose ---------------------
    dt = np.diff(t_ev) / 1e3
    gaps = []
    for k in np.flatnonzero((dt > GAP_MS) & air[1:]):
        i, j = max(0, k - 5), min(len(t_ev) - 1, k + 6)
        gaps.append({"t_s": float((t_ev[k] - t_ev[i0]) / 1e6), "gap_ms": float(dt[k]),
                     "speed_mps": float(np.linalg.norm(vg[k, :2])), "yaw_rate_dps": float(np.degrees(abs(wg[k, 2]))),
                     "pos_err_change_m": float(np.linalg.norm(perr[j, :2] - perr[i, :2])),
                     "yaw_err_change_deg": float(np.degrees(wrap(yerr[min(len(t_ev) - 1, k + 30)] - yerr[max(0, k - 30)])))})
    rep["frame_gaps"] = {"count": len(gaps), "gaps": gaps,
                         "p99_dt_ms": float(np.percentile(dt[air[1:]], 99)),
                         "worst_slip_m": max((g["pos_err_change_m"] for g in gaps), default=0.0),
                         "worst_yaw_slip_deg": max((abs(g["yaw_err_change_deg"]) for g in gaps), default=0.0)}

    # ---- tilt of the EV frame (roll/pitch vs truth; a pure heading offset does not change them) ---------------------
    (re_, pe_), (rt_, pt_) = roll_pitch(q_ev), roll_pitch(qg)
    tilt = np.degrees(np.hypot(wrap(re_ - rt_), wrap(pe_ - pt_)))
    first, last = air & (t_ev < t_ev[i0] + 2e6), air & (t_ev > t_ev[air][-1] - 2e6)
    rep["tilt"] = {"start_deg": float(np.median(tilt[first])), "end_deg": float(np.median(tilt[last])),
                   "median_deg": float(np.median(tilt[air])),
                   "roll_err_median_deg": float(np.degrees(np.median(wrap(re_ - rt_)[air]))),
                   "pitch_err_median_deg": float(np.degrees(np.median(wrap(pe_ - pt_)[air])))}

    # ---- EKF2 -----------------------------------------------------------------------------------------------------
    flags = d.get("estimator_status_flags") or {}
    for src, key in (("ev_pos", "ev_pos_fused_min"), ("ev_vel", "ev_vel_fused_min")):
        if f"cs_{src}" in flags:                       # published on change: hold each value until the next one
            k = np.searchsorted(flags["timestamp"].astype(float), t_ev[air], side="right") - 1
            on_in_air = np.any(flags[f"cs_{src}"][k[k >= 0]])
        else:
            on_in_air = True
        if not on_in_air:
            ekf.setdefault(src, {})["note"] = "not enabled (EKF2_EV_CTRL): no fused gate"   # an ablation config, not a fault
            continue
        if src in ekf and ekf[src]["fused"] < GATES[key]:
            fails.append(f"{src} fused {ekf[src]['fused']:.2f}")
    if ekf["position_error"]["horiz_max_m"] > GATES["ekf_horiz_max_m"]:
        fails.append(f"EKF2 horizontal max {ekf['position_error']['horiz_max_m']:.2f} m")
    rep["ekf2"] = ekf
    rep["gates"], rep["fails"] = GATES, fails
    ser = {"tt": (t_ev - t_ev[i0]) / 1e6, "air": air, "perr": perr, "yerr": yerr, "y_gt": y_gt, "verr": v_ev - vc,
           "disp_gt": disp_gt, "disp_ev": disp_ev, "tte": (ser_e["te"] - ser_e["te"][ser_e["j0"]]) / 1e6, **ser_e}
    return rep, fails, ser


def write_series(ser, path, hz=5.0):
    """t since takeoff, EKF2 horizontal + z error, ZED horizontal + yaw error, at `hz` (the report's error-over-time figure)."""
    me, tte, ee = ser["me"], ser["tte"], ser["ee"]
    t = np.arange(0.0, tte[me][-1], 1.0 / hz)
    air = ser["air"]
    cols_ = {"t_s": t,
             "ekf_horiz_err_m": np.interp(t, tte[me], np.linalg.norm(ee[me, :2], axis=1)),
             "ekf_z_err_m": np.interp(t, tte[me], ee[me, 2]),
             "ev_horiz_err_m": np.interp(t, ser["tt"][air], np.linalg.norm(ser["perr"][air, :2], axis=1)),
             "ev_yaw_err_deg": np.interp(t, ser["tt"][air], np.degrees(ser["yerr"][air]))}
    with open(path, "w") as fh:
        fh.write(",".join(cols_) + "\n")
        for row in zip(*cols_.values()):
            fh.write(",".join(f"{v:.4f}" for v in row) + "\n")


def plot(ser, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tt, air, me, tte, ee = ser["tt"], ser["air"], ser["me"], ser["tte"], ser["ee"]
    fig, ax = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    ax[0].plot(tt[air], ser["perr"][air, 0], ".", ms=2, label="EV x")
    ax[0].plot(tt[air], ser["perr"][air, 1], ".", ms=2, label="EV y")
    ax[0].plot(tte[me], ee[me, 0], lw=1, label="EKF2 x")
    ax[0].plot(tte[me], ee[me, 1], lw=1, label="EKF2 y")
    ax[0].set_ylabel("pos error vs truth [m]")
    ax[0].legend(ncol=4)
    ax[1].plot(tt[air], np.degrees(ser["yerr"][air]), ".", ms=2, label="EV yaw error")
    ax[1].set_ylabel("yaw error [deg]")
    ax2 = ax[1].twinx()
    ax2.plot(tt, np.degrees(ser["y_gt"]), "k", lw=0.6, alpha=0.5)
    ax2.set_ylabel("true yaw [deg]")
    for k, lab in enumerate(("vx", "vy", "vz")):
        ax[2].plot(tt[air], ser["verr"][air, k], ".", ms=2, label=lab)
    ax[2].set_ylabel("EV vel error (body) [m/s]")
    ax[2].legend(ncol=3)
    ax[3].plot(tt, ser["disp_gt"][:, 2], "k", lw=1, label="truth z (NED)")
    ax[3].plot(tt, ser["disp_ev"][:, 2], lw=1, label="EV z (not fused)")
    ax[3].set_ylabel("height disp. [m]")
    ax[3].set_xlabel("s since takeoff")
    ax[3].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--ulog", help="PX4 log of the flight")
    src.add_argument("--npz", help="an extract written by --save-npz (archive/vio-*/<run>/topics.npz)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plot", action="store_true", help="vio_eval.png (needs matplotlib)")
    ap.add_argument("--series", action="store_true", help="series.csv: errors over time at 5 Hz (for tests/vio_report.py)")
    ap.add_argument("--save-npz", default="", help="write the fields read here to this .npz (for the archive)")
    ap.add_argument("--air-margin", type=float, default=0.15, help="m above the resting height that counts as airborne")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    d = load(a.ulog or a.npz)
    if a.save_npz:
        save_npz(d, a.save_npz)
    rep, fails, ser = analyse(d, a.air_margin)
    with open(os.path.join(a.out, "vio_eval.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps(rep, indent=1))
    if a.series and ser is not None:
        write_series(ser, os.path.join(a.out, "series.csv"))
    if a.plot and ser is not None:
        plot(ser, os.path.join(a.out, "vio_eval.png"))
    print("PASS" if not fails else f"FAIL: {'; '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
