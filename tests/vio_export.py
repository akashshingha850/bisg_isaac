#!/usr/bin/env python3
"""
Export VIO campaigns (tests/vio_campaign.py) to figure-ready JSON (docs/vio-campaign.md). Python stdlib only.

    python3 tests/vio_export.py $ARCHIVE_DIR/vio_bench/*/ --out docs/data/vio_campaigns.json
writes
  <out>              every campaign: setup, verdict + checks, per-config statistics (all / event-free flights), ablation deltas vs
                     `calibrated`, ZED pipeline calibration, reliability, every flight's scalar metrics and its events
                     (yaw steps, frame gaps, pose jumps); plus `history` (one row per campaign) and `metric_definitions`
  <out>_series.json  per campaign, per flight: the 5 Hz error series of series.csv as column arrays (error-over-time figures)
NaN is written as null. The numbers are vio_report.py's (same METRICS getters, same statistics, same verdict).
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vio_report as vr  # noqa: E402

SCHEMA = 1
# Pegasus spawn height on the floor (truth z at the start of tests/vio_bench.py): names the world of campaigns that predate the
# `world` field of vio_campaign.py stack_versions() (added 2026-10-17)
WORLD_BY_SPAWN_Z = [(-0.67, "Simple Room"), (0.10, "Warehouse")]
DESCRIPTIONS = {
    "ekf_h_max": "max over the airborne samples of |EKF2 - truth| in x/y (displacements from takeoff)",
    "ekf_h_end": "|EKF2 - truth| in x/y at the last airborne sample",
    "ekf_h_rms": "hypot of the x and y RMSE of EKF2 vs truth",
    "ekf_z_max": "max |EKF2 z - truth z|",
    "ev_h_max": "max horizontal error of the ZED position as EKF2 received it (lever arm removed, start-aligned)",
    "ev_yaw_end": "|ZED yaw - truth yaw| at the end, after removing the constant start offset",
    "ekf_yaw_end": "|EKF2 yaw - truth yaw| at the end",
    "yaw_step_worst": "largest yaw error a single rotation (|yaw rate| > 0.3 rad/s) added to the ZED",
    "yaw_rate_peak": "peak |yaw rate| over the rotations (set by MC_YAWRATE_MAX)",
    "latency": "best lag of the EV velocity against truth (+-300 ms search); residual after the bridge restamp, should be ~0",
    "vel_rmse": "ZED body velocity RMSE, x and y combined per axis (hypot / sqrt 2)",
    "vel_scale_x": "least-squares slope ZED vs true camera velocity, body x (1 = right scale and frame)",
    "vel_scale_y": "same, body y",
    "lever_fit": "|true camera offset - EKF2_EV_POS| in x/y fitted from the hover yaw steps",
    "pos_noise": "short-term ZED position noise: std of the residual after a 2 s moving average (worse axis)",
    "gaps": "EV gaps > 150 ms while airborne",
    "gap_slip": "largest position-error change across a frame gap",
    "gap_yaw_slip": "largest yaw-error change across a frame gap",
    "pose_jump": "largest ZED position step (> 0.10 m off truth between two samples, no gap)",
    "tilt_end": "ZED roll/pitch vs truth at the end (world-frame tilt of the IMU-less sim SDK)",
    "ev_pos_fused": "fraction of EV position samples EKF2 fused",
    "flow_fused": "fraction of optical-flow samples EKF2 fused",
}


def clean(x, nd=6):
    """JSON-safe: NaN/inf -> None, floats rounded."""
    if isinstance(x, float):
        return None if math.isnan(x) or math.isinf(x) else round(x, nd)
    if isinstance(x, dict):
        return {k: clean(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v, nd) for v in x]
    return x


def world_of(versions, runs):
    w = versions.get("world")
    if w:
        return os.path.splitext(os.path.basename(w))[0].replace("warehouse", "Warehouse"), "recorded"
    for r in runs:
        log = os.path.join(r["_path"], "bench.log")
        if os.path.exists(log):
            m = re.search(r"start est=\[[^\]]*\] truth=\[[-0-9., ]+?, [-0-9.]+, ([-0-9.]+)\]", open(log).read())
            if m:
                z = float(m.group(1))
                name = min(WORLD_BY_SPAWN_Z, key=lambda p: abs(p[0] - z))
                if abs(name[0] - z) < 0.1:
                    return name[1], f"inferred from the spawn height z {z:+.2f} m"
    return None, "unknown"


def flight_record(r):
    e = r["eval"] or {}
    rec = {"id": r["dir"], "config": r["config"], "rep": r.get("rep"), "status": r.get("status"), "attempts": r.get("attempts"),
           "params_applied": r.get("params_applied"), "ekf_ev_flags_preflight": r.get("ekf_ev_flags_preflight"),
           "flight_rc": r.get("flight_rc"), "flight_wall_s": r.get("flight_wall_s"), "rtf": r.get("rtf"),
           "zed_alive_after": r.get("zed_alive_after"), "infra_failures": r.get("infra_failures", []),
           "gates_passed": r["passed"], "fails": e.get("fails", []), "dominant_event": r["event"],
           "event_free": r["event"] == "none (drift)", "metrics": r["metrics"]}
    if e.get("ev_present"):
        pe = e["ekf2"]["position_error"]
        rec.update(
            airborne_s=e.get("airborne_s"), path_m=e["position"].get("path_m"),
            ev_drift_pct_of_path=e["position"].get("drift_pct_of_path"), ev_rate_hz=e["ev_frames"].get("rate_hz"),
            ekf_error_axes={ax: {k: pe[ax][k] for k in ("bias", "std", "rmse", "p95_abs", "max_abs")} for ax in "xyz"},
            ev_velocity_axes={ax: {k: e["velocity_body"][ax][k] for k in ("bias", "rmse", "scale", "corr")} for ax in "xyz"},
            lever_arm_fit_xy_m=e["lever_arm_fit"].get("delta_xy_m"),
            ekf2_fusion={src: {k: v for k, v in s.items() if k in ("n", "fused", "rejected", "test_ratio_p95")}
                         for src, s in e["ekf2"].items() if isinstance(s, dict) and "fused" in s},
            yaw_steps=e["yaw_steps"]["steps"], frame_gaps=e["frame_gaps"]["gaps"], pose_jumps=e["pose_jumps"]["jumps"])
    return rec


def campaign(camp):
    plan, machine, runs = vr.load(camp)
    for r in runs:
        r["_path"] = os.path.join(camp, "runs", r["dir"])
    names = [n for n in plan["selected_configs"] if any(r["config"] == n for r in runs)]
    by = {n: [r for r in runs if r["config"] == n] for n in names}
    flown = [r for r in runs if r["metrics"]]
    stats = {n: {k: vr.describe([r["metrics"].get(k) for r in rs if r["metrics"]]) for k in vr.METRICS} for n, rs in by.items()}
    free = {n: {k: vr.describe([r["metrics"].get(k) for r in rs if r["metrics"] and r["event"] == "none (drift)"])
                for k in vr.METRICS} for n, rs in by.items()}
    verdict, checks, suggest = vr.verify(plan, runs)
    vv = {**vr.DEFAULT_VERIFY, **plan.get("verify", {})}
    versions = next((r["versions"] for r in runs if r.get("versions")), {})
    world, world_src = world_of(versions, runs)
    rtfs = [r["rtf"]["median"] for r in runs if r.get("rtf", {}).get("median")]
    infra = [{"flight": r["dir"], **f} for r in runs for f in r.get("infra_failures", [])]
    lim = vv["performance_horiz_max_m"]
    deltas = {}
    if "calibrated" in names:
        base = stats["calibrated"]
        deltas = {n: {k: (stats[n][k]["mean"] - base[k]["mean"] if stats[n][k].get("n") and base[k].get("n") else None)
                      for k in vr.METRICS} for n in names if n != "calibrated"}
    cid = os.path.basename(camp.rstrip("/"))
    kind = "ablation" if len(names) > 1 else ("verification" if len(runs) > 1 else "check")
    restamp = plan.get("restamp_latency_ms")
    out = {
        "id": cid, "kind": kind, "date": machine.get("date"), "host": machine.get("host"),
        "world": world, "world_source": world_src,
        "world_lights": versions.get("world_lights") or None, "ambient_light": versions.get("ambient_light") or None,
        "restamp_latency_ms": restamp if isinstance(restamp, (int, float)) and not math.isnan(restamp) else None,
        "configs_flown": names, "reps": plan["reps"], "view": plan["view"], "scenario": plan.get("scenario"),
        "config_params": {n: plan["configs"][n]["params"] or {} for n in names},
        "verify_thresholds": vv,
        "verdict": verdict, "checks": [{"check": c, "pass": ok, "value": v} for c, ok, v in checks], "suggestions": suggest,
        "machine": machine, "versions": versions,
        "rtf": vr.describe(rtfs),
        "reliability": {"boots": sum(r.get("attempts", len(r.get("infra_failures", []))) for r in runs),
                        "infra_failures": infra, "flights_done": sum(r.get("status") == "done" for r in runs),
                        "flights_given_up": sum(r.get("status") == "infra_failed" for r in runs)},
        "per_config": {n: {"flights": len([r for r in by[n] if r["metrics"]]),
                           "within_performance_bound": sum(r["metrics"]["ekf_h_max"] <= lim for r in by[n] if r["metrics"]),
                           "performance_bound_m": lim,
                           "events": {ev: sum(1 for r in by[n] if r["metrics"] and r["event"] == ev) for ev in vr.EVENTS},
                           "stats": stats[n], "stats_event_free": free[n],
                           "delta_mean_vs_calibrated": deltas.get(n)} for n in names},
        "pipeline_calibration_all_flights": {k: vr.describe([r["metrics"].get(k) for r in flown]) for k in vr.CALIB},
        "flights": [flight_record(r) for r in runs],
    }
    series = {r["dir"]: r["series"] for r in runs if r["series"]}
    cal = [r["metrics"]["ekf_h_max"] for r in runs if r["config"] == "calibrated" and r["metrics"]]
    hist = {"id": cid, "kind": kind, "date": out["date"], "world": world, "world_lights": out["world_lights"],
            "ambient_light": out["ambient_light"], "restamp_latency_ms": out["restamp_latency_ms"], "flights": len(flown),
            "verdict": verdict, "rtf_median": out["rtf"].get("median"),
            "residual_latency_ms_median": st.median(r["metrics"]["latency"] for r in flown) if flown else None,
            "calibrated_ekf_h_max_mean_m": st.fmean(cal) if cal else None, "calibrated_ekf_h_max_worst_m": max(cal) if cal else None,
            "flights_with_sdk_event": sum(r["event"] != "none (drift)" for r in flown), "infra_failures": len(infra),
            "boots": out["reliability"]["boots"]}
    return out, series, hist


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("campaigns", nargs="+", help="campaign dirs (with summary inputs: campaign.json, machine.json, runs/)")
    ap.add_argument("--out", required=True, help="results JSON; the series go to <out minus .json>_series.json")
    a = ap.parse_args(argv)
    camps, series, history = [], {}, []
    for c in sorted(a.campaigns, key=lambda p: os.path.basename(p.rstrip("/"))):
        if not os.path.exists(os.path.join(c, "campaign.json")):
            print(f"skip {c}: no campaign.json", file=sys.stderr)
            continue
        out, ser, hist = campaign(c)
        camps.append(out)
        series[out["id"]] = ser
        history.append(hist)
        print(f"{out['id']}: {out['kind']}, {out['world']}, {len(out['flights'])} flights, {out['verdict']}")
    base = os.path.splitext(a.out)[0]
    doc = {"schema_version": SCHEMA, "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "generator": "tests/vio_export.py", "documentation": "docs/vio-campaign.md", "series_file": os.path.basename(base) + "_series.json",
           "metric_definitions": {k: {"label": lab, "unit": unit, "decimals": dec, "description": DESCRIPTIONS.get(k, "")}
                                  for k, (lab, unit, dec, _) in vr.METRICS.items()},
           "events": vr.EVENTS, "history": history, "campaigns": camps}
    with open(a.out, "w") as fh:
        json.dump(clean(doc), fh, indent=1)
    with open(base + "_series.json", "w") as fh:
        json.dump(clean({"schema_version": SCHEMA, "rate_hz": 5.0, "time": "s since takeoff",
                         "columns": {"ekf_horiz_err_m": "|EKF2 - truth| x/y [m]", "ekf_z_err_m": "EKF2 - truth z [m] (signed)",
                                     "ev_horiz_err_m": "|ZED - truth| x/y [m]", "ev_yaw_err_deg": "ZED - truth yaw [deg] (signed)"},
                         "campaigns": series}, 4), fh, separators=(",", ":"))
    print(f"wrote {a.out} and {base}_series.json")


if __name__ == "__main__":
    main()
