#!/usr/bin/env python3
"""Analysis for the VO/perception study (docs/study-vo-perception.md). Needs numpy, scipy, matplotlib: run it in the Isaac image

    scripts/study_analyze.sh logs/study/d1

Inputs  <run>/truth.csv clock.csv odom_live.csv marks.log   (tests/study/record_run.py + fly_profile.py)
        <run>/../results/<run>/<config>_r<k>/pose.csv summary.json depth_s8.npz   (tests/study/svo_bench.py)
Outputs <run>/analysis/metrics.csv (one row per configuration run), configs.csv (median over repeats), depth_range.csv, figures.

Accuracy of a pose estimate is judged against the simulator's ground truth for the CAMERA (body pose + the ZED mount offset):
  ate_start   RMSE of the position error when the SDK world frame is tied to the truth at the FIRST frame (what PX4 sees:
              one fixed frame, no per-run best fit)                                                     [m]
  ate_flight  ate_start restricted to the flight (until the landing begins): the landing close to the floor is a special case
  err_at_land position error when the landing starts [m]
  ate_se3     RMSE after the best rigid fit over the whole run (shape accuracy, hides a wrong start)     [m]
  end_err     position error at the last frame; drift = end_err / path length                           [m, %]
  rpe_1s      RMS of the position error change over 1 s of sim time, per metre travelled              [m/m]
  rot_rpe_1s  RMS of the heading error change over 1 s                                                  [deg]
  scale       SDK path length / true path length
  jumps       frame-to-frame position steps > 0.5 m or > 25 deg (tracking resets / relocalisation)
"""
import csv
import glob
import json
import os
import re
import sys

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

MOUNT = np.array([0.18, 0.0, -0.02])      # ZED Mini on the Iris body, FLU (sim/configs/*.yaml mount_xyz_rpy)


def load(path):
    return np.genfromtxt(path, delimiter=",", names=True)


class Truth:
    def __init__(self, d):
        t, c = load(d + "/truth.csv"), load(d + "/clock.csv")
        self.clock_wall, self.clock_sim = c["recv"], c["sim"]
        ts = np.interp(t["stamp"], self.clock_wall, self.clock_sim)
        keep = np.concatenate([[True], np.diff(ts) > 1e-6])
        self.t = ts[keep]
        self.p = np.stack([t["x"], t["y"], t["z"]], 1)[keep]
        self.R = Rotation.from_quat(np.stack([t["qx"], t["qy"], t["qz"], t["qw"]], 1)[keep])
        self.slerp = Slerp(self.t, self.R)
        self.marks = []
        for line in open(d + "/marks.log"):
            m = re.match(r"MARK (\w+) sim=([\d.]+)", line)
            if m:
                self.marks.append((m.group(1), float(m.group(2))))

    def cam(self, ts):
        """Camera position + rotation at sim times ts (clipped to the truth span)."""
        ts = np.clip(ts, self.t[0], self.t[-1])
        p = np.stack([np.interp(ts, self.t, self.p[:, i]) for i in range(3)], 1)
        R = self.slerp(ts)
        return p + R.apply(MOUNT), R

    def phases(self):
        out = []
        for i, (n, s) in enumerate(self.marks[:-1]):
            out.append((n, s, self.marks[i + 1][1]))
        return out


def umeyama(src, dst):
    """Rigid (no scale) best fit dst ~ R src + t."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    H = (src - mu_s).T @ (dst - mu_d)
    U, _, Vt = np.linalg.svd(H)
    S = np.eye(3)
    S[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ S @ U.T
    return R, mu_d - R @ mu_s


def metrics(tr, ts, ps, qs, c_off, name=""):
    """ts sim times of the SDK frames, ps (N,3) SDK positions, qs (N,4) SDK quats."""
    t_sim = ts - c_off
    pc, Rc = tr.cam(t_sim)
    Rs = Rotation.from_quat(qs)
    R0, p0 = Rc[0], pc[0]
    # SDK world tied to the truth at the first frame: position in the camera's start frame, then truth start pose
    est = R0.apply(Rs[0].inv().apply(ps - ps[0])) + p0
    err = est - pc
    ate_start = float(np.sqrt((err ** 2).sum(1).mean()))
    R, t = umeyama(ps, pc)
    err_se3 = (ps @ R.T + t) - pc
    ate_se3 = float(np.sqrt((err_se3 ** 2).sum(1).mean()))
    path_true = float(np.linalg.norm(np.diff(pc, axis=0), axis=1).sum())
    path_est = float(np.linalg.norm(np.diff(ps, axis=0), axis=1).sum())
    # RPE over 1 s of sim time
    j = np.searchsorted(t_sim, t_sim + 1.0)
    ok = j < len(t_sim)
    i = np.arange(len(t_sim))[ok]
    j = j[ok]
    d_est, d_true = est[j] - est[i], pc[j] - pc[i]
    dist = np.linalg.norm(d_true, axis=1)
    rpe = float(np.sqrt(((d_est - d_true) ** 2).sum(1).mean()) / max(dist.mean(), 1e-6))
    rot_est = (Rs[i].inv() * Rs[j])
    rot_true = (Rc[i].inv() * Rc[j])
    rot_err = (rot_true.inv() * rot_est).magnitude()
    rot_rpe = float(np.degrees(np.sqrt((rot_err ** 2).mean())))
    step = np.linalg.norm(np.diff(ps, axis=0), axis=1)
    rstep = np.degrees((Rs[:-1].inv() * Rs[1:]).magnitude())
    jumps = int(((step > 0.5) | (rstep > 25)).sum())
    land = dict(tr.marks).get("land")
    fm = t_sim < land if land else np.ones(len(t_sim), bool)
    ate_flight = float(np.sqrt((err[fm] ** 2).sum(1).mean())) if fm.any() else float("nan")
    err_at_land = float(np.linalg.norm(err[fm][-1])) if fm.any() else float("nan")
    phases = {}
    for n, a, b in tr.phases():
        m = (t_sim >= a) & (t_sim < b)
        if m.sum() > 3:
            phases[n] = float(np.sqrt((err[m] ** 2).sum(1).mean()))
    return dict(ate_start=ate_start, ate_flight=ate_flight, err_at_land=err_at_land, ate_se3=ate_se3, end_err=float(np.linalg.norm(err[-1])), path_true=path_true,
                drift_pct=100 * float(np.linalg.norm(err[-1])) / max(path_true, 1e-6), rpe_1s=rpe, rot_rpe_1s=rot_rpe,
                scale=path_est / max(path_true, 1e-6), jumps=jumps, max_err=float(np.linalg.norm(err, axis=1).max()),
                **{f"ph_{k}": v for k, v in phases.items()}), est, pc, t_sim


DEPTH_BINS = [(1, 2), (2, 3), (3, 4), (4, 6), (6, 8), (8, 12), (12, 15)]


def floor_depth_errors(tr, c_off, depth_file, calib, zf, frames=None):
    """Depth error on pixels whose ray hits the floor plane z = zf: measured Z minus the Z the truth predicts.
    Returns (z_expected, error, valid) flattened over the selected frames; error NaN where the SDK has no depth."""
    f = np.load(depth_file)
    D, st = f["depth"], f["stamp"]
    fx, fy, cx, cy = calib["fx"], calib["fy"], calib["cx"], calib["cy"]
    v, u = np.mgrid[0:D.shape[1], 0:D.shape[2]]
    u, v = u * 8.0, v * 8.0
    dc = np.stack([np.ones_like(u), -(u - cx) / fx, -(v - cy) / fy], -1).reshape(-1, 3)
    ze, er, va = [], [], []
    for k in range(len(D)):
        if frames is not None and k not in frames:
            continue
        t = st[k] * 1e-9 - c_off
        if t < tr.t[0] or t > tr.t[-1]:
            continue
        pc, R = tr.cam(np.array([t]))
        dw = R.apply(dc)
        zexp = (zf - pc[0, 2]) / dw[:, 2]
        m = (dw[:, 2] < -0.02) & (zexp > 0.5) & (zexp < 15.0)
        z = D[k].reshape(-1)
        ok = np.isfinite(z) & (z > 0.3) & (z < 15.0)
        ze.append(zexp[m]); va.append(ok[m]); er.append(np.where(ok[m], z[m] - zexp[m], np.nan))
    if not ze:
        return np.zeros(0), np.zeros(0), np.zeros(0, bool)
    return np.concatenate(ze), np.concatenate(er), np.concatenate(va)


def fit_floor(tr, c_off, depth_file, calib, hover_frames):
    best = None
    for zf in np.arange(-0.2, 0.21, 0.02):
        ze, er, va = floor_depth_errors(tr, c_off, depth_file, calib, zf, hover_frames)
        m = va & (ze > 3) & (ze < 8)
        if m.sum() < 100:
            continue
        sc = np.nanmedian(np.abs(er[m]) / ze[m])
        if best is None or sc < best[0]:
            best = (sc, zf)
    return best[1] if best else 0.0


def depth_report(tr, c_off, res, calib, out):
    """Per-config depth quality on the floor, per range bin. Frames: the flight phases at altitude (floor visible, level camera)."""
    files = {}
    for sd in sorted(glob.glob(res + "/*_r0/")):
        if os.path.exists(sd + "depth_s8.npz"):
            files[os.path.basename(sd.rstrip("/"))[:-3]] = sd + "depth_s8.npz"
    if not files:
        return
    fly = [(a, b) for n, a, b in tr.phases() if n in ("hover", "sq_fwd", "sq_left", "sq_back", "sq_right", "spin", "hover2", "hover3")]
    ref = files.get("np_only") or files.get("g3_np") or next(iter(files.values()))
    st = np.load(ref)["stamp"] * 1e-9 - c_off
    sel = {k for k in range(len(st)) if any(a <= st[k] < b for a, b in fly)}
    zf = fit_floor(tr, c_off, ref, calib, sel)
    print(f"floor height fitted on {os.path.basename(ref)}: z = {zf:+.2f} m")
    rows = []
    for name, fpath in files.items():
        ze, er, va = floor_depth_errors(tr, c_off, fpath, calib, zf, sel)
        for lo, hi in DEPTH_BINS:
            m = (ze >= lo) & (ze < hi)
            if m.sum() < 50:
                continue
            e, z, v_ = er[m], ze[m], va[m]
            ok = np.isfinite(e)
            rel = np.abs(e[ok]) / z[ok]
            rows.append(dict(config=name, bin=f"{lo}-{hi}", n=int(m.sum()), valid_frac=float(v_.mean()),
                             med_err_m=float(np.median(e[ok])) if ok.any() else float("nan"),
                             mad_sigma_m=float(1.4826 * np.median(np.abs(e[ok] - np.median(e[ok])))) if ok.any() else float("nan"),
                             med_rel_err_pct=100 * float(np.median(rel)) if ok.any() else float("nan"),
                             within5pct=float((rel < 0.05).sum() / m.sum()), within10pct=float((rel < 0.10).sum() / m.sum())))
    if not rows:
        return
    with open(out + "/depth_range.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    json.dump({"floor_z": zf}, open(out + "/depth_floor.json", "w"))


def find_offsets(tr, odom):
    """Constant mapping from SDK stamps to sim time: stamp = sim + C. C0 from the receive times, refined by the best fit."""
    sim_recv = np.interp(odom["recv"], tr.clock_wall, tr.clock_sim)
    c0 = float(np.median(odom["stamp"] - sim_recv))
    ps = np.stack([odom["x"], odom["y"], odom["z"]], 1)
    best = None
    for d in np.arange(-0.6, 0.61, 0.02):
        m, *_ = metrics(tr, odom["stamp"], ps, np.stack([odom["qx"], odom["qy"], odom["qz"], odom["qw"]], 1), c0 + d)
        if best is None or m["ate_se3"] < best[0]:
            best = (m["ate_se3"], d)
    return c0 + best[1], best[1], c0


def main():
    d = sys.argv[1].rstrip("/")
    run = os.path.basename(d)
    res = os.path.join(os.path.dirname(d), "results", run)
    out = os.path.join(d, "analysis")
    os.makedirs(out, exist_ok=True)
    tr = Truth(d)
    odom = load(d + "/odom_live.csv")
    c_off, lag, c0 = find_offsets(tr, odom)
    print(f"stamp->sim offset C={c_off:.3f} (receive-time estimate {c0:.3f}, refined by {lag:+.2f} s)")
    live_m, *_ = metrics(tr, odom["stamp"], np.stack([odom["x"], odom["y"], odom["z"]], 1),
                         np.stack([odom["qx"], odom["qy"], odom["qz"], odom["qw"]], 1), c_off)
    print("live wrapper odometry (GEN_3 default) ate_start %.3f ate_se3 %.3f" % (live_m["ate_start"], live_m["ate_se3"]))

    rows, tracks = [], {}
    for sd in sorted(glob.glob(res + "/*_r*/")):
        name = os.path.basename(sd.rstrip("/"))
        cfg, rep = name.rsplit("_r", 1)
        if not os.path.exists(sd + "summary.json"):
            continue
        s = json.load(open(sd + "summary.json"))
        row = dict(config=cfg, repeat=int(rep), fps_max=s["fps_max"], grab_ms_mean=s["grab_ms_mean"], grab_ms_p95=s["grab_ms_p95"],
                   grab_ms_max=s["grab_ms_max"], cpu_cores=s["cpu_cores_avg"], cpu_ms_frame=s["cpu_ms_per_frame"],
                   gpu_util=s["gpu_util_mean"], gpu_vram_mib=s["gpu_mem_used_mib_max"] - s["gpu_mem_baseline_mib"],
                   gpu_w=s["gpu_power_w_mean"], rss_mib=s["max_rss_mib"], frames=s["frames_processed"],
                   ok_frames=s["tracking_ok_frames"], open_s=s["open_s"])
        pf = sd + "pose.csv"
        if s["config"]["tracking"] != "NONE" and os.path.exists(pf):
            p = np.genfromtxt(pf, delimiter=",", names=True, dtype=None, encoding=None)
            if len(p) > 20:
                ts = p["stamp_ns"] * 1e-9
                ps = np.stack([p["x"], p["y"], p["z"]], 1)
                qs = np.stack([p["qx"], p["qy"], p["qz"], p["qw"]], 1)
                # time offset: one constant per run, tuned within +-0.25 s to the best flight-phase fit (standard practice: it
                # removes the stamp/render-lag uncertainty that the truth association cannot resolve better than ~0.1 s);
                # the untuned numbers are kept as *_g
                mg, *_ = metrics(tr, ts, ps, qs, c_off)
                best = None
                for dlt in np.arange(-0.25, 0.2501, 0.01):
                    mm, *_ = metrics(tr, ts, ps, qs, c_off + dlt)
                    if best is None or mm["ate_flight"] < best[0]:
                        best = (mm["ate_flight"], dlt)
                m, est, pc, t_sim = metrics(tr, ts, ps, qs, c_off + best[1])
                row.update(m)
                row["dt_best"] = float(best[1])
                row["ate_flight_g"], row["ate_start_g"], row["err_at_land_g"] = mg["ate_flight"], mg["ate_start"], mg["err_at_land"]
                row["not_ok_pct"] = 100.0 * float(np.mean(p["state"] != "OK"))
                tracks[name] = (t_sim, est, pc)
        rows.append(row)
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(out + "/metrics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    # median over repeats
    cfgs = sorted({r["config"] for r in rows})
    med = []
    for c in cfgs:
        rr = [r for r in rows if r["config"] == c]
        o = {"config": c, "repeats": len(rr)}
        for k in cols:
            if k in ("config", "repeat"):
                continue
            v = [r[k] for r in rr if k in r and isinstance(r[k], (int, float))]
            if v:
                o[k] = float(np.median(v))
                o[k + "_min"], o[k + "_max"] = float(np.min(v)), float(np.max(v))
        med.append(o)
    mcols = []
    for r in med:
        for k in r:
            if k not in mcols:
                mcols.append(k)
    with open(out + "/configs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=mcols)
        w.writeheader()
        w.writerows(med)
    json.dump({"offset_C": c_off, "live": live_m}, open(out + "/live_baseline.json", "w"), indent=1)
    if os.path.exists(d + "/calib.json"):
        depth_report(tr, c_off, res, json.load(open(d + "/calib.json")), out)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # trajectory overlay + error vs time for a few representative runs
        pick = [n for n in ("g3_nl_r0", "g3_none_r0", "g1_nl_r0", "g1_np_r0") if n in tracks]
        if pick:
            fig, ax = plt.subplots(1, 2, figsize=(13, 5))
            t0, _, pc = tracks[pick[0]]
            ax[0].plot(pc[:, 0], pc[:, 1], "k", lw=2, label="truth (camera)")
            for n in pick:
                t, est, _ = tracks[n]
                ax[0].plot(est[:, 0], est[:, 1], lw=1, label=n[:-3])
                _, e, p_ = tracks[n]
                ax[1].plot(t, np.linalg.norm(e - p_, axis=1), label=n[:-3])
            ax[0].set_aspect("equal"); ax[0].set_xlabel("x east [m]"); ax[0].set_ylabel("y north [m]"); ax[0].legend(); ax[0].set_title("top view")
            ax[1].set_xlabel("sim time [s]"); ax[1].set_ylabel("position error [m]"); ax[1].legend(); ax[1].set_title("error vs time (start-aligned)")
            for n_, a_, b_ in tr.phases():
                ax[1].axvline(a_, color="0.8", lw=0.6)
                ax[1].text(a_, ax[1].get_ylim()[1] * 0.95, n_, rotation=90, fontsize=7, va="top")
            fig.tight_layout(); fig.savefig(out + "/trajectories.png", dpi=110); plt.close(fig)
        # ranking bars
        rr = sorted([r for r in med if "ate_flight" in r], key=lambda r: r["ate_flight"])
        if rr:
            fig, ax = plt.subplots(figsize=(9, 0.28 * len(rr) + 1.5))
            col = lambda c: "tab:green" if c.startswith("cu_") else ("tab:blue" if c.startswith("g3") else ("tab:orange" if c.startswith("g1") else "tab:red"))
            ax.barh([r["config"] for r in rr][::-1], [r["ate_flight"] for r in rr][::-1], color=[col(r["config"]) for r in rr][::-1])
            ax.set_xscale("log"); ax.set_xlabel("ATE during flight, start-aligned [m] (log)  green=cuVSLAM blue=ZED GEN_3 orange=GEN_1 red=GEN_2")
            fig.tight_layout(); fig.savefig(out + "/ranking.png", dpi=110); plt.close(fig)
        # speed vs accuracy
        fig, ax = plt.subplots(figsize=(7, 5))
        for r in med:
            if "ate_flight" in r:
                ax.scatter(r["grab_ms_mean"], r["ate_flight"], s=40)
                ax.annotate(r["config"], (r["grab_ms_mean"], r["ate_flight"]), fontsize=7)
        ax.set_xscale("log"); ax.set_xlabel("grab() time per frame [ms] (RTX 4500 Ada)"); ax.set_ylabel("ATE during flight, start-aligned [m]")
        ax.set_title("tracking: cost vs accuracy"); fig.tight_layout(); fig.savefig(out + "/cost_vs_accuracy.png", dpi=110); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print("plots skipped:", exc)
    print(f"{len(rows)} runs, {len(cfgs)} configurations -> {out}")


if __name__ == "__main__":
    main()
