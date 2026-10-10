#!/usr/bin/env python3
"""
Accuracy of the ToF rangefinder + optical-flow twins against ground truth (docs/range-flow.md), from the PX4 log of a
tests/range_flow_bench.py flight (+ its ROS CSVs). numpy only: runs on the host or in any container.

Ground truth = PX4's `vehicle_*_groundtruth` topics, sent by sim/launcher/range_flow.py (`sensors.ground_truth`) on the
same clock as `distance_sensor` and `vehicle_optical_flow`, so no cross-clock alignment is needed. A residual lag is
still measured (best shift in ±200 ms).

What is checked, and why the gates are what they are (they test the TWIN, not a real LW20/C or PMW3901):
  ToF   range vs slant distance to the floor along body +Z (flat floor at --floor-z).   gate: |bias| <= 1 cm,
        RMSE <= 2 x the configured noise (--tof-noise), < 1 % outliers (> 10 cm): the twin is a ray + N(0, noise) + 1 cm steps.
  flow  gyro-compensated flow rate vs (-v_y, v_x)/range from ground-truth body velocity; gyro vs ground-truth rates.
        gate: RMSE <= 2 x --flow-noise per axis, scale (LS slope) 0.95-1.05, the twin's model is exact otherwise.
  EKF2  flow / range fusion (fused fraction, innovation test ratios) and position vs ground truth.
        gate: flow fused >= 90 % of airborne samples with quality > 0, p95 test ratio < 1, horizontal error <= 0.3 m
        (the Phase 3 bound, tests/vio_flight.py).
  ROS   mavros/hrlv_ez4_pub (what the companion sees): rate, frame, error vs Pegasus state/pose (reported, not gated).

    python3 tests/range_flow_eval.py --ulog <flight.ulg> --ros-dir <bench out dir> --out <report dir>
Exit 0 = every gate passes.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ulog_lite  # noqa: E402

TOPICS = ["distance_sensor", "vehicle_optical_flow", "vehicle_local_position", "vehicle_local_position_groundtruth",
          "vehicle_attitude_groundtruth", "vehicle_angular_velocity_groundtruth", "estimator_aid_src_optical_flow",
          "estimator_aid_src_rng_hgt", "estimator_status_flags"]


# ---- helpers -------------------------------------------------------------------------------------------------------
def interp(ts, y, t):
    return np.interp(t, ts, y, left=np.nan, right=np.nan)


def quat_interp(ts, q, t):
    q = q.copy()
    for i in range(1, len(q)):                       # keep sign continuity before linear interpolation
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
    out = np.stack([interp(ts, q[:, k], t) for k in range(4)], axis=1)
    return out / np.linalg.norm(out, axis=1, keepdims=True)


def rot(q):
    """(N,4) w,x,y,z (FRD body -> NED) -> (N,3,3)."""
    w, x, y, z = q.T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], axis=1)


def stats(err):
    err = err[np.isfinite(err)]
    if err.size == 0:
        return {"n": 0}
    return {"n": int(err.size), "bias": float(err.mean()), "std": float(err.std()),
            "rmse": float(np.sqrt(np.mean(err ** 2))), "p95_abs": float(np.percentile(np.abs(err), 95)),
            "max_abs": float(np.abs(err).max())}


def slope(meas, exp):
    ok = np.isfinite(meas) & np.isfinite(exp)
    if ok.sum() < 10 or np.dot(exp[ok], exp[ok]) < 1e-9:
        return float("nan"), float("nan")
    k = float(np.dot(exp[ok], meas[ok]) / np.dot(exp[ok], exp[ok]))
    c = float(np.corrcoef(meas[ok], exp[ok])[0, 1])
    return k, c


def best_lag(f_err, lags_s):
    """f_err(lag_s) -> error array; returns (lag at min RMSE, rmse at 0, rmse at best)."""
    rmses = []
    for lag in lags_s:
        e = f_err(lag)
        e = e[np.isfinite(e)]
        rmses.append(np.sqrt(np.mean(e ** 2)) if e.size else np.inf)
    i = int(np.argmin(rmses))
    i0 = int(np.argmin(np.abs(lags_s)))
    return float(lags_s[i]), float(rmses[i0]), float(rmses[i])


def binned(x, err, edges):
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (x >= lo) & (x < hi) & np.isfinite(err)
        if m.sum():
            s = stats(err[m])
            rows.append({"bin": f"{lo:g}-{hi:g}", "n": s["n"], "mean": s["bias"], "rmse": s["rmse"]})
    return rows


def held(ts_flags, values, t):
    """Sample-and-hold a published-on-change flag at times t."""
    i = np.searchsorted(ts_flags, t, side="right") - 1
    out = np.zeros(len(t), dtype=bool)
    ok = i >= 0
    out[ok] = values[i[ok]].astype(bool)
    return out


# ---- main analysis -------------------------------------------------------------------------------------------------
class GT:
    def __init__(self, d, gt_alt0, floor_z, mount_flu):
        lp, att, av = (d["vehicle_local_position_groundtruth"], d["vehicle_attitude_groundtruth"],
                       d["vehicle_angular_velocity_groundtruth"])
        self.t_lp, self.lp = lp["timestamp"].astype(float), lp
        self.t_att = att["timestamp"].astype(float)
        self.q = np.stack([att[f"q[{i}]"] for i in range(4)], 1).astype(float)
        self.t_av = av["timestamp"].astype(float)
        self.w = np.stack([av[f"xyz[{i}]"] for i in range(3)], 1).astype(float)
        self.z0_world = float(lp["ref_alt"][0]) - gt_alt0      # world z of the PX4 ground-truth origin
        self.floor_z = floor_z
        self.mount = np.array([mount_flu[0], -mount_flu[1], -mount_flu[2]])   # FLU -> FRD

    def at(self, t):
        """Ground truth at times t (us): R, v_ned, v_body, w_body, height of the sensor, slant range along body +Z."""
        R = rot(quat_interp(self.t_att, self.q, t))
        v_ned = np.stack([interp(self.t_lp, self.lp[k].astype(float), t) for k in ("vx", "vy", "vz")], 1)
        v_body = np.einsum("nji,nj->ni", R, v_ned)
        w = np.stack([interp(self.t_av, self.w[:, k], t) for k in range(3)], 1)
        z = interp(self.t_lp, self.lp["z"].astype(float), t)
        h_body = self.z0_world - z - self.floor_z
        h_sensor = h_body - np.einsum("nij,j->ni", R, self.mount)[:, 2]
        r22 = R[:, 2, 2]
        slant = np.where(r22 > 0.2, h_sensor / r22, np.nan)
        return {"R": R, "v_ned": v_ned, "v_body": v_body + np.cross(w, self.mount), "w": w,
                "h": h_sensor, "slant": slant, "pos": np.stack([interp(self.t_lp, self.lp[k].astype(float), t)
                                                               for k in ("x", "y", "z")], 1)}


def eval_tof(d, gt, noise):
    ds = d.get("distance_sensor")
    if ds is None:
        return {"error": "no distance_sensor in the log"}, False
    t = ds["timestamp"].astype(float)
    meas = ds["current_distance"].astype(float)
    dmin, dmax = float(ds["min_distance"][0]), float(ds["max_distance"][0])
    valid = (meas >= dmin) & (meas <= dmax)

    def err_at(lag_s):
        g = gt.at(t + lag_s * 1e6)
        return np.where(valid, meas - g["slant"], np.nan)
    lags = np.arange(-0.2, 0.2001, 0.005)
    lag, rmse0, rmse_best = best_lag(err_at, lags)
    g = gt.at(t)
    err = np.where(valid, meas - g["slant"], np.nan)
    expect_valid = (g["slant"] >= dmin) & (g["slant"] <= dmax)
    s = stats(err)
    outliers = float(np.mean(np.abs(err[np.isfinite(err)]) > 0.10)) if s["n"] else 1.0
    dur = (t[-1] - t[0]) / 1e6
    res = {"n": int(len(t)), "rate_hz": float(len(t) / dur) if dur > 0 else 0.0, "min_m": dmin, "max_m": dmax,
           "error": s, "outlier_frac_gt10cm": outliers,
           "valid_when_expected": float(np.mean(valid[expect_valid])) if expect_valid.any() else None,
           "lag_best_ms": lag * 1e3, "rmse_lag0": rmse0, "rmse_best_lag": rmse_best,
           "h_range_m": [float(np.nanmin(g["h"])), float(np.nanmax(g["h"]))],
           "by_height": binned(g["h"], err, [0, 0.3, 1, 2, 3, 4, 5, 100]),
           "by_tilt_deg": binned(np.degrees(np.arccos(np.clip(g["R"][:, 2, 2], -1, 1))), err, [0, 2, 5, 10, 20, 45])}
    ok = s["n"] > 0 and abs(s["bias"]) <= 0.01 and s["rmse"] <= 2 * noise and outliers <= 0.01
    res["gate"] = {"bias_le_m": 0.01, "rmse_le_m": 2 * noise, "outliers_le": 0.01, "pass": bool(ok)}
    return res, ok


def eval_flow(d, gt, noise):
    f = d.get("vehicle_optical_flow")
    if f is None:
        return {"error": "no vehicle_optical_flow in the log"}, False
    span = f["integration_timespan_us"].astype(float)
    ok_span = span > 0
    t_end = f["timestamp_sample"].astype(float)
    dt = np.where(ok_span, span * 1e-6, np.nan)
    raw = np.stack([f["pixel_flow[0]"], f["pixel_flow[1]"]], 1).astype(float) / dt[:, None]
    gyro = np.stack([f[f"delta_angle[{i}]"] for i in range(3)], 1).astype(float) / dt[:, None]
    comp = raw - gyro[:, :2]
    q = f["quality"].astype(int)
    good = ok_span & (q > 0)

    def expected(lag_s):
        g = gt.at(t_end - span / 2 + lag_s * 1e6)               # mid-window
        e = np.stack([-g["v_body"][:, 1] / g["slant"], g["v_body"][:, 0] / g["slant"]], 1)
        return g, e

    def err_at(lag_s):
        _, e = expected(lag_s)
        return np.where(good[:, None], comp - e, np.nan).ravel()
    lag, rmse0, rmse_best = best_lag(err_at, np.arange(-0.2, 0.2001, 0.005))
    g, e = expected(0.0)
    err = np.where(good[:, None], comp - e, np.nan)
    gerr = np.where(good[:, None], gyro[:, :2] - g["w"][:, :2], np.nan)
    # velocity domain: what EKF2 effectively gets, flow x range
    v_meas = np.stack([comp[:, 1] * g["slant"], -comp[:, 0] * g["slant"]], 1)
    verr = np.where(good[:, None], v_meas - g["v_body"][:, :2], np.nan)
    speed = np.linalg.norm(g["v_body"][:, :2], axis=1)
    kx, cx = slope(np.where(good, comp[:, 0], np.nan), e[:, 0])
    ky, cy = slope(np.where(good, comp[:, 1], np.nan), e[:, 1])
    dist_err = np.where(good, f["distance_m"].astype(float) - g["slant"], np.nan)
    h = g["h"]
    qual = [{"bin": f"{lo:g}-{hi:g}", "n": int(m.sum()), "quality_gt0": float(np.mean(q[m] > 0))}
            for lo, hi in zip([-1, 0.08, 0.5, 2, 4, 5], [0.08, 0.5, 2, 4, 5, 100])
            for m in [(h >= lo) & (h < hi) & ok_span] if m.sum()]
    sx, sy = stats(err[:, 0]), stats(err[:, 1])
    res = {"n": int(len(t_end)), "n_quality_gt0": int(good.sum()),
           "rate_hz": float(len(t_end) / ((t_end[-1] - t_end[0]) / 1e6)) if len(t_end) > 1 else 0.0,
           "integration_ms_median": float(np.median(span[ok_span]) / 1e3) if ok_span.any() else None,
           "comp_flow_err_rad_s": {"x": sx, "y": sy}, "scale": {"x": kx, "y": ky}, "corr": {"x": cx, "y": cy},
           "gyro_err_rad_s": {"x": stats(gerr[:, 0]), "y": stats(gerr[:, 1])},
           "velocity_err_m_s": {"fwd": stats(verr[:, 0]), "right": stats(verr[:, 1])},
           "distance_err_m": stats(dist_err), "lag_best_ms": lag * 1e3, "rmse_lag0": rmse0, "rmse_best_lag": rmse_best,
           "max_speed_m_s": float(np.nanmax(np.where(good, speed, np.nan))) if good.any() else None,
           "vel_err_by_speed": binned(speed, np.linalg.norm(verr, axis=1), [0, 0.25, 0.75, 1.5, 3, 10]),
           "vel_err_by_height": binned(h, np.linalg.norm(verr, axis=1), [0, 0.5, 1, 2, 3, 4, 5]),
           "quality_by_height": qual}
    lim = 2 * noise
    ok = (sx["n"] > 0 and sx["rmse"] <= lim and sy["rmse"] <= lim and 0.95 <= kx <= 1.05 and 0.95 <= ky <= 1.05)
    res["gate"] = {"rmse_le_rad_s": lim, "scale_in": [0.95, 1.05], "pass": bool(ok)}
    return res, ok


def eval_ekf(d, gt, max_h_err):
    lp = d["vehicle_local_position"]
    t = lp["timestamp_sample"].astype(float)
    g = gt.at(t)
    airborne = g["h"] > 0.2
    est = np.stack([lp[k].astype(float) for k in ("x", "y", "z")], 1)
    vest = np.stack([lp[k].astype(float) for k in ("vx", "vy", "vz")], 1)
    first = np.flatnonzero(np.isfinite(g["pos"][:, 0]))[0]
    off = est[first] - g["pos"][first]                          # EKF origin != ground-truth origin
    perr = est - off - g["pos"]
    verr = vest - g["v_ned"]
    herr = np.linalg.norm(perr[:, :2], axis=1)
    path = np.nansum(np.linalg.norm(np.diff(g["pos"][:, :2], axis=0), axis=1))
    i_air = np.flatnonzero(airborne & np.isfinite(herr))
    last_air = i_air[-1]
    end = np.flatnonzero(np.isfinite(herr))[-1]
    # height: z error relative to the on-ground value at the start (the EKF origin height differs from ground truth's)
    ground0 = (~airborne) & (np.arange(len(t)) < i_air[0])
    z_off = np.nanmedian(perr[ground0, 2]) if ground0.any() else 0.0
    res = {"airborne_s": float(airborne.sum() / max(1, len(t)) * (t[-1] - t[0]) / 1e6),
           "horiz_err_m": {"max": float(np.nanmax(herr[airborne])), "rms": float(np.sqrt(np.nanmean(herr[airborne] ** 2))),
                           "last_airborne": float(herr[last_air]), "after_landing": float(herr[end])},
           "height_err_m": stats(perr[airborne, 2] - z_off),     # NED z: negative = EKF thinks higher than truth
           "vel_err_m_s": {"n": stats(verr[airborne, 0]), "e": stats(verr[airborne, 1]), "d": stats(verr[airborne, 2])},
           "path_m": float(path),
           "drift_pct_of_path": float(100 * herr[last_air] / path) if path > 0 else None}
    if "dist_bottom" in lp:
        hb = lp["dist_bottom"].astype(float)
        hv = lp["dist_bottom_valid"].astype(bool) if "dist_bottom_valid" in lp else np.ones(len(t), bool)
        res["dist_bottom_valid_frac"] = float(hv[airborne].mean())
        res["dist_bottom_err_m"] = stats(np.where(airborne, hb - g["h"], np.nan))   # EKF HAGL vs truth, flag ignored
    fused_ok = True
    for name, key in (("estimator_aid_src_optical_flow", "flow"), ("estimator_aid_src_rng_hgt", "range")):
        a = d.get(name)
        if a is None:
            res[key] = {"error": f"no {name}"}
            fused_ok = False
            continue
        ta = a["timestamp_sample"].astype(float)
        air = gt.at(ta)["h"] > 0.2
        tr = np.stack([a[k].astype(float) for k in a if k.startswith("test_ratio[")], 1) if "test_ratio[0]" in a \
            else a["test_ratio"].astype(float)[:, None]
        inn = np.stack([a[k].astype(float) for k in a if k.startswith("innovation[")], 1) if "innovation[0]" in a \
            else a["innovation"].astype(float)[:, None]
        fused = a["fused"].astype(bool)
        res[key] = {"n_airborne": int(air.sum()), "fused_frac": float(fused[air].mean()) if air.any() else None,
                    "rejected_frac": float(a["innovation_rejected"].astype(bool)[air].mean()) if air.any() else None,
                    "test_ratio_p50": float(np.nanpercentile(tr[air].max(1), 50)) if air.any() else None,
                    "test_ratio_p95": float(np.nanpercentile(tr[air].max(1), 95)) if air.any() else None,
                    "innovation_rms": [float(np.sqrt(np.nanmean(inn[air, k] ** 2))) for k in range(inn.shape[1])]}
    sf = d.get("estimator_status_flags")
    if sf is not None:
        ts = sf["timestamp"].astype(float)
        tt = t[airborne]
        res["airborne_time_frac"] = {k: float(held(ts, sf[k], tt).mean())
                                     for k in ("cs_opt_flow", "cs_rng_hgt", "cs_inertial_dead_reckoning") if k in sf}
    fl = res.get("flow", {})
    ok = (fused_ok and fl.get("fused_frac") is not None and fl["fused_frac"] >= 0.9 and fl["test_ratio_p95"] < 1.0
          and res["horiz_err_m"]["max"] <= max_h_err)
    res["gate"] = {"flow_fused_ge": 0.9, "flow_test_ratio_p95_lt": 1.0, "horiz_err_max_le_m": max_h_err, "pass": bool(ok)}
    return res, ok


def eval_ros(ros_dir, floor_z):
    rp, gp = os.path.join(ros_dir, "range.csv"), os.path.join(ros_dir, "gt.csv")
    if not (os.path.exists(rp) and os.path.exists(gp)):
        return {"error": f"no range.csv / gt.csv in {ros_dir}"}

    def load(p):
        with open(p) as fh:
            rows = list(csv.DictReader(fh))
        return rows
    rr, gg = load(rp), load(gp)
    if not rr or not gg:
        return {"error": "empty CSV", "n_range": len(rr), "n_gt": len(gg)}
    tg = np.array([float(r["t_recv"]) for r in gg])
    o = np.argsort(tg)
    tg = tg[o]
    zg = np.array([float(r["z"]) for r in gg])[o]
    qg = np.array([[float(r[k]) for k in ("qw", "qx", "qy", "qz")] for r in gg])[o]
    # ENU/FLU: body z axis in world = third column of R; its world-z component = R22 (same as the NED/FRD case)
    r22 = rot(qg)[:, 2, 2]
    tr = np.array([float(r["t_recv"]) for r in rr])
    meas = np.array([float(r["range"]) for r in rr])
    dmin, dmax = float(rr[0]["min_range"]), float(rr[0]["max_range"])
    valid = (meas > dmin) & (meas < dmax)      # == max: the twin's "no reading" code; <= min: below the sensor's range

    def err_at(lag):
        h = interp(tg, zg - floor_z, tr - lag)
        c = interp(tg, r22, tr - lag)
        return np.where(valid, meas - h / c, np.nan)
    lag, rmse0, rmse_best = best_lag(err_at, np.arange(0.0, 0.5001, 0.01))
    ground = np.array([r["phase"] == "ground" for r in rr])
    dur = tr[-1] - tr[0]
    return {"topic": "mavros/hrlv_ez4_pub", "n": int(len(rr)), "rate_hz_sim": float(len(rr) / dur) if dur > 0 else 0.0,
            "frame_id": rr[0]["frame_id"], "min_range": dmin, "max_range": dmax,
            "no_reading_frac": float(np.mean(meas >= dmax)), "at_or_below_min_frac": float(np.mean(meas <= dmin)),
            "invalid_on_ground_frac": float(np.mean(~valid[ground])) if ground.any() else None,
            "on_ground_m": float(np.median(meas[ground & valid])) if (ground & valid).any() else None,
            "gt_height_on_ground_m": float(np.median(interp(tg, zg, tr[ground]))) if ground.any() else None,
            "error_at_best_lag": stats(err_at(lag)), "lag_best_ms": lag * 1e3, "rmse_lag0": rmse0,
            "note": "receive-time alignment; PX4 streams DISTANCE_SENSOR at ~10 Hz and truncates m -> cm "
                    "(mavlink/streams/DISTANCE_SENSOR.hpp), so a reading can lose up to 1 cm here (not in the uORB ToF)"}


def fmt(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def markdown(r):
    t, f, e = r["tof"], r["flow"], r["ekf"]
    L = [f"# Range + flow benchmark — {os.path.basename(r['ulog'])}", "",
         "Sim twins (sim/launcher/range_flow.py) vs PX4 ground truth. Gates test the twin, not real sensors.", "",
         "| Check | Result | Gate | Pass |", "|---|---|---|---|"]
    if "error" in t and isinstance(t["error"], dict):
        s = t["error"]
        L.append(f"| ToF error (m) | bias {fmt(s.get('bias'), 4)}, RMSE {fmt(s.get('rmse'), 4)}, p95 {fmt(s.get('p95_abs'), 4)}, "
                 f"outliers {fmt(t['outlier_frac_gt10cm'], 4)} | |bias| ≤ {t['gate']['bias_le_m']}, RMSE ≤ "
                 f"{t['gate']['rmse_le_m']} | {'PASS' if t['gate']['pass'] else 'FAIL'} |")
    if "comp_flow_err_rad_s" in f:
        L.append(f"| flow comp. error (rad/s) | x RMSE {fmt(f['comp_flow_err_rad_s']['x'].get('rmse'), 4)}, "
                 f"y RMSE {fmt(f['comp_flow_err_rad_s']['y'].get('rmse'), 4)}; scale x {fmt(f['scale']['x'])}, "
                 f"y {fmt(f['scale']['y'])} | RMSE ≤ {f['gate']['rmse_le_rad_s']}, scale 0.95-1.05 | "
                 f"{'PASS' if f['gate']['pass'] else 'FAIL'} |")
    if "horiz_err_m" in e:
        fl = e.get("flow", {})
        L.append(f"| EKF2 flow fusion / position | fused {fmt(fl.get('fused_frac'))}, test ratio p95 "
                 f"{fmt(fl.get('test_ratio_p95'))}, horiz. max err {fmt(e['horiz_err_m']['max'])} m | ≥ 0.9, < 1, ≤ "
                 f"{e['gate']['horiz_err_max_le_m']} m | {'PASS' if e['gate']['pass'] else 'FAIL'} |")
    L += ["", "Full numbers: `report.json` next to this file."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ulog", required=True)
    ap.add_argument("--ros-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--gt-alt0", type=float, default=100.0, help="range_flow.GT_ALT0")
    ap.add_argument("--floor-z", type=float, default=0.0, help="world z of the (flat) floor under the flight")
    ap.add_argument("--mount", default="0,0,0", help="ToF/flow mount, base_link FLU m (scenario mount_xyz)")
    ap.add_argument("--tof-noise", type=float, default=0.01, help="scenario sensors.tof.noise_std_m")
    ap.add_argument("--flow-noise", type=float, default=0.02, help="scenario sensors.optical_flow.noise_std_rad_s")
    ap.add_argument("--max-horiz-err", type=float, default=0.3)
    a = ap.parse_args()

    d = ulog_lite.read(a.ulog, TOPICS)
    missing = [k for k in TOPICS[:6] if k not in d]
    if missing:
        print(f"[range_flow_eval] missing in the log: {missing} (ground truth needs sensors.ground_truth.enabled)")
        return 2
    gt = GT(d, a.gt_alt0, a.floor_z, [float(v) for v in a.mount.split(",")])
    report = {"ulog": a.ulog}
    report["tof"], ok_t = eval_tof(d, gt, a.tof_noise)
    report["flow"], ok_f = eval_flow(d, gt, a.flow_noise)
    report["ekf"], ok_e = eval_ekf(d, gt, a.max_horiz_err)
    if a.ros_dir:
        report["ros"] = eval_ros(a.ros_dir, a.floor_z)
    report["pass"] = bool(ok_t and ok_f and ok_e)
    md = markdown(report)
    print(md)
    print(json.dumps(report, indent=1, default=float))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "report.json"), "w") as fh:
            json.dump(report, fh, indent=1, default=float)
        with open(os.path.join(a.out, "report.md"), "w") as fh:
            fh.write(md)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
