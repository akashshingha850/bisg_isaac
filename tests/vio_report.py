#!/usr/bin/env python3
"""
Summary, calibration check and verdict of a VIO campaign (tests/vio_campaign.py, `./bisg vio report <dir>`). Python stdlib only.

Reads <dir>/campaign.json, machine.json and runs/*/{run.json, vio_eval.json, series.csv}; writes
  summary.md     experimental setup (machine, software, scenario, profile, configs), results per config (mean +- std, min-max),
                 ablation deltas vs `calibrated`, calibration check with suggested corrections, reliability, per-flight table
  summary.json   the same numbers, machine-readable;  summary.csv   one row per flight
  figures/*.svg  per-config bars (mean +- std, every flight as a dot) and EKF2 / ZED error over time
Verdict (exit 0 = PASS) from the `verify` block of the campaign config: pipeline checks on every flight that reached the air,
outcome checks on the `calibrated` flights. INCOMPLETE (exit 2) when there is nothing to judge.
"""
import csv
import glob
import json
import math
import os
import re
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# metric key -> (label, unit, decimals, getter on vio_eval.json)
METRICS = {
    "ekf_h_max": ("EKF2 horizontal error, max", "m", 3, lambda r: r["ekf2"]["position_error"]["horiz_max_m"]),
    "ekf_h_end": ("EKF2 horizontal error, end", "m", 3, lambda r: r["ekf2"]["position_error"]["horiz_end_m"]),
    "ekf_h_rms": ("EKF2 horizontal RMS", "m", 3, lambda r: math.hypot(r["ekf2"]["position_error"]["x"]["rmse"],
                                                                      r["ekf2"]["position_error"]["y"]["rmse"])),
    "ekf_z_max": ("EKF2 height error, max", "m", 3, lambda r: r["ekf2"]["position_error"]["z"]["max_abs"]),
    "ev_h_max": ("ZED horizontal error, max", "m", 3, lambda r: r["position"]["horiz_max_m"]),
    "ev_yaw_end": ("ZED yaw error, end |.|", "deg", 2, lambda r: abs(r["yaw"]["end_deg"])),
    "ekf_yaw_end": ("EKF2 yaw error, end |.|", "deg", 2, lambda r: abs(r["yaw"].get("ekf_end_deg", float("nan")))),
    "yaw_step_worst": ("worst yaw slip per rotation", "deg", 2, lambda r: r["yaw_steps"]["worst_ev_err_added_deg"]),
    "yaw_rate_peak": ("peak yaw rate", "deg/s", 0, lambda r: r["yaw_steps"]["peak_rate_dps"]),
    "latency": ("residual EV latency", "ms", 0, lambda r: r["latency_ms"]["best_lag_ms"]),
    "vel_rmse": ("ZED velocity RMSE (x,y)", "m/s", 3, lambda r: math.hypot(r["velocity_body"]["x"]["rmse"],
                                                                         r["velocity_body"]["y"]["rmse"]) / math.sqrt(2)),
    "vel_scale_x": ("ZED velocity scale x", "", 3, lambda r: r["velocity_body"]["x"]["scale"]),
    "vel_scale_y": ("ZED velocity scale y", "", 3, lambda r: r["velocity_body"]["y"]["scale"]),
    "lever_fit": ("lever-arm fit |.|", "m", 3, lambda r: math.hypot(*r["lever_arm_fit"]["delta_xy_m"])),
    "pos_noise": ("ZED position noise (2 s HP)", "m", 4, lambda r: max(r["position"]["hf_noise_std_m"].values())),
    "gaps": ("EV gaps > 150 ms", "", 1, lambda r: r["frame_gaps"]["count"]),
    "gap_slip": ("worst slip at a gap", "m", 3, lambda r: r["frame_gaps"]["worst_slip_m"]),
    "gap_yaw_slip": ("worst yaw slip at a gap", "deg", 2, lambda r: r["frame_gaps"].get("worst_yaw_slip_deg", float("nan"))),
    "pose_jump": ("worst pose jump (no gap)", "m", 3, lambda r: r.get("pose_jumps", {}).get("worst_m", float("nan"))),
    "tilt_end": ("ZED frame tilt, end", "deg", 2, lambda r: r["tilt"]["end_deg"]),
    "ev_pos_fused": ("EV position fused", "", 3, lambda r: r["ekf2"].get("ev_pos", {}).get("fused", float("nan"))),
    "flow_fused": ("optical flow fused", "", 3, lambda r: r["ekf2"].get("optical_flow", {}).get("fused", float("nan"))),
}
TABLE = ["ekf_h_max", "ekf_h_end", "ekf_h_rms", "ekf_z_max", "ev_yaw_end", "ekf_yaw_end", "yaw_step_worst", "yaw_rate_peak",
         "gaps", "gap_slip", "gap_yaw_slip", "pose_jump", "tilt_end"]
EVENTS = ["none (drift)", "slip at a frame gap", "yaw slip at a frame gap", "pose jump (no gap)", "yaw slip in a rotation"]
CALIB = ["latency", "vel_scale_x", "vel_scale_y", "vel_rmse", "lever_fit", "pos_noise"]
FIGS = ["ekf_h_max", "ekf_h_end", "ekf_z_max", "ev_yaw_end", "yaw_step_worst", "gap_slip", "pose_jump"]
DEFAULT_VERIFY = {"latency_abs_ms": 20, "vel_scale_err": 0.03, "lever_arm_m": 0.03, "event_free_horiz_max_m": 0.25,
                  "performance_horiz_max_m": 0.30}
COLORS = ["#2a6fdb", "#e0663a", "#2e9e5b", "#9b51e0", "#c9a227", "#d6457a", "#4aa3a2", "#7a7a7a"]


def read_json(path):
    with open(path) as fh:
        return json.load(fh)


def write(path, text):
    with open(path, "w") as fh:
        fh.write(text)


def num(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def describe(vals):
    v = [x for x in vals if num(x)]
    if not v:
        return {"n": 0}
    return {"n": len(v), "mean": st.fmean(v), "std": st.stdev(v) if len(v) > 1 else 0.0, "min": min(v), "max": max(v),
            "median": st.median(v)}


def fmt(d, dec, unit=""):
    if not d or d.get("n", 0) == 0:
        return "-"
    s = f"{d['mean']:.{dec}f}"
    if d["n"] > 1:
        s += f" ± {d['std']:.{dec}f} ({d['min']:.{dec}f}-{d['max']:.{dec}f})"
    return s


# ---- load ------------------------------------------------------------------------------------------------------------
def load(camp):
    plan = read_json(os.path.join(camp, "campaign.json"))
    machine = read_json(os.path.join(camp, "machine.json"))
    runs = []
    for p in sorted(glob.glob(os.path.join(camp, "runs", "*", "run.json"))):
        run = read_json(p)
        d = os.path.dirname(p)
        run["dir"] = os.path.basename(d)
        ev = os.path.join(d, "vio_eval.json")
        run["eval"] = read_json(ev) if os.path.exists(ev) else None
        run["metrics"] = {}
        if run["eval"] and run["eval"].get("ev_present"):
            for k, (_, _, _, get) in METRICS.items():
                try:
                    run["metrics"][k] = float(get(run["eval"]))
                except (KeyError, TypeError, ValueError):
                    run["metrics"][k] = float("nan")
        run["passed"] = bool(run["eval"] and not run["eval"].get("fails"))
        run["event"] = (run["eval"] or {}).get("dominant_event", "-")
        run["series"] = read_series(os.path.join(d, "series.csv"))
        runs.append(run)
    return plan, machine, runs


def read_series(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    return {k: [float(r[k]) for r in rows] for k in rows[0]} if rows else None


def file_value(path, pattern):
    try:
        with open(os.path.join(ROOT, path)) as fh:
            m = re.search(pattern, fh.read(), re.M)
        return float(m.group(1)) if m else None
    except OSError:
        return None


# ---- verdict + calibration -------------------------------------------------------------------------------------------
def verify(plan, runs):
    v = {**DEFAULT_VERIFY, **plan.get("verify", {})}
    flown = [r for r in runs if r["metrics"]]
    checks, suggest = [], []
    if not flown:
        return "INCOMPLETE", [("flights with ZED data", False, "none")], suggest
    lat = st.median(r["metrics"]["latency"] for r in flown)
    cur = plan.get("restamp_latency_ms")                                        # the value the campaign flew with
    if cur is None or (isinstance(cur, float) and math.isnan(cur)):
        cur = file_value("docker/zed/zed.yaml", r"^\s*restamp_latency_ms:\s*([0-9.]+)\s*#\s*measured")
    checks.append((f"residual EV latency |median| <= {v['latency_abs_ms']} ms", abs(lat) <= v["latency_abs_ms"], f"{lat:+.0f} ms"))
    if cur is not None and (abs(lat) > v["latency_abs_ms"] / 2 or (abs(lat) > 5 and len(flown) >= 3)):   # one flight: ~3 ms noise
        suggest.append(f"docker/zed/zed.yaml `sim.services.px4_bridge.odometry.restamp_latency_ms`: {cur:g} -> {cur + lat:.0f} "
                       f"(residual {lat:+.0f} ms at this machine's RTF)")
    for ax in "xy":
        s = st.median(r["metrics"][f"vel_scale_{ax}"] for r in flown)
        checks.append((f"ZED velocity scale {ax} within ±{v['vel_scale_err']}", abs(s - 1) <= v["vel_scale_err"], f"{s:.3f}"))
    fits = [r["eval"]["lever_arm_fit"]["delta_xy_m"] for r in flown
            if r["eval"]["lever_arm_fit"].get("hover_rotations", 1) and all(num(x) for x in r["eval"]["lever_arm_fit"]["delta_xy_m"])]
    if fits:
        fx, fy = st.median(f[0] for f in fits), st.median(f[1] for f in fits)
        checks.append((f"lever-arm fit from hover yaw steps |median| <= {v['lever_arm_m']} m ({len(fits)} flights)",
                       math.hypot(fx, fy) <= v["lever_arm_m"], f"({fx:+.4f}, {fy:+.4f}) m"))
        if math.hypot(fx, fy) > v["lever_arm_m"] / 2 and len(fits) >= 3:
            px = file_value("docker/sim/px4/raptor.params", r"^EKF2_EV_POS_X\s+([-0-9.]+)")
            py = file_value("docker/sim/px4/raptor.params", r"^EKF2_EV_POS_Y\s+([-0-9.]+)")
            suggest.append(f"the sim ZED's effective camera position is ({fx:+.3f}, {fy:+.3f}) m (FRD) off EKF2_EV_POS_X/Y {px:g}/{py:g}: "
                           "check the twin's mount (raptor.yaml sensors.zed) before touching raptor.params, which is the REAL mount")
    else:
        checks.append(("lever-arm fit", True, "no hover yaw steps in these flights: not checked"))
    cal = [r for r in runs if r["config"] == "calibrated" and r["metrics"]]
    free = [r for r in cal if r["event"] == "none (drift)"]
    if free:
        worst = max(r["metrics"]["ekf_h_max"] for r in free)
        checks.append((f"event-free calibrated flights: EKF2 horizontal max <= {v['event_free_horiz_max_m']} m",
                       worst <= v["event_free_horiz_max_m"], f"worst {worst:.3f} m over {len(free)}/{len(cal)} flights"))
    else:
        checks.append(("event-free calibrated flights", False, f"none of {len(cal)} (fly more: --reps)"))
    return ("PASS" if all(c[1] for c in checks) else "FAIL"), checks, suggest


# ---- SVG figures (no matplotlib needed) ------------------------------------------------------------------------------
def nice_max(x):
    if x <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 2.5, 5, 10):
        if x <= m * e:
            return m * e
    return 10 * e


def svg_bars(path, title, unit, names, groups, ref=None, hollow=None):
    """groups: per name the flight values; hollow: per name, per flight True = drawn as an open circle (a flight with an SDK event)."""
    W, H, L, R, T, B = 760, 380, 70, 20, 40, 95
    vals = [x for g in groups for x in g if num(x)]
    top = nice_max(max(vals + [ref or 0]) * 1.1 if vals else 1)
    y = lambda v: T + (H - T - B) * (1 - v / top)
    bw = (W - L - R) / max(len(names), 1)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="15" font-weight="bold">{title}</text>']
    for i in range(6):
        v = top * i / 5
        o.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e3e3e3"/>')
        o.append(f'<text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    o.append(f'<text x="16" y="{(T + H - B) / 2}" transform="rotate(-90 16 {(T + H - B) / 2})" text-anchor="middle">{unit}</text>')
    if ref is not None:
        o.append(f'<line x1="{L}" x2="{W - R}" y1="{y(ref):.1f}" y2="{y(ref):.1f}" stroke="#c0392b" stroke-dasharray="6 4"/>')
        o.append(f'<text x="{W - R}" y="{y(ref) - 5:.1f}" text-anchor="end" fill="#c0392b">gate {ref:g}</text>')
    for i, (n, g) in enumerate(zip(names, groups)):
        x0, c = L + i * bw, COLORS[i % len(COLORS)]
        d = describe(g)
        if d["n"]:
            o.append(f'<rect x="{x0 + bw * 0.2:.1f}" y="{y(d["mean"]):.1f}" width="{bw * 0.6:.1f}" '
                     f'height="{y(0) - y(d["mean"]):.1f}" fill="{c}" fill-opacity="0.35" stroke="{c}"/>')
            if d["n"] > 1:
                xm = x0 + bw / 2
                o.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{y(min(top, d["mean"] + d["std"])):.1f}" '
                         f'y2="{y(max(0, d["mean"] - d["std"])):.1f}" stroke="#222" stroke-width="1.5"/>')
            flags = [h for x_, h in zip(g, (hollow or [[]] * len(groups))[i] or [False] * len(g)) if num(x_)]
            for k, v in enumerate(x for x in g if num(x)):
                fill = "white" if k < len(flags) and flags[k] else c
                o.append(f'<circle cx="{x0 + bw * (0.35 + 0.3 * k / max(d["n"] - 1, 1)):.1f}" cy="{y(min(v, top)):.1f}" r="3.8" '
                         f'fill="{fill}" stroke="{c}" stroke-width="1.6"/>')
        o.append(f'<text x="{x0 + bw / 2:.1f}" y="{H - B + 16}" text-anchor="end" '
                 f'transform="rotate(-30 {x0 + bw / 2:.1f} {H - B + 16})">{n}</text>')
    if hollow:
        o.append(f'<text x="{W - R}" y="{H - 8}" text-anchor="end" fill="#666">filled dot = flight, open dot = flight with an SDK event</text>')
    o.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#444"/></svg>')
    write(path, "\n".join(o))


def svg_series(path, title, unit, names, curves, events=None):
    """curves: per name a list of (t, v) lists; draws every flight thin and the per-config mean thick."""
    W, H, L, R, T, B = 760, 380, 70, 150, 40, 50
    tmax = max((s[0][-1] for c in curves for s in c if s and s[0]), default=1.0)
    vmax = nice_max(max((max(s[1]) for c in curves for s in c if s and s[1]), default=1.0))
    x = lambda t: L + (W - L - R) * t / tmax
    y = lambda v: T + (H - T - B) * (1 - min(v, vmax) / vmax)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{(W - R + L) / 2}" y="22" text-anchor="middle" font-size="15" font-weight="bold">{title}</text>']
    for i in range(6):
        v = vmax * i / 5
        o.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e3e3e3"/>')
        o.append(f'<text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    step = nice_max(tmax / 6)
    t = 0.0
    while t <= tmax:
        o.append(f'<text x="{x(t):.1f}" y="{H - B + 16}" text-anchor="middle">{t:g}</text>')
        t += step
    o.append(f'<text x="{(W - R + L) / 2}" y="{H - 12}" text-anchor="middle">s since takeoff</text>')
    o.append(f'<text x="16" y="{(T + H - B) / 2}" transform="rotate(-90 16 {(T + H - B) / 2})" text-anchor="middle">{unit}</text>')
    for label, (t0, t1) in (events or {}).items():
        if t1 <= tmax:
            o.append(f'<rect x="{x(t0):.1f}" y="{T}" width="{x(t1) - x(t0):.1f}" height="{H - T - B}" fill="#f2f2f2"/>')
            o.append(f'<text x="{(x(t0) + x(t1)) / 2:.1f}" y="{T + 12}" text-anchor="middle" fill="#888">{label}</text>')
    for i, (n, c) in enumerate(zip(names, curves)):
        col = COLORS[i % len(COLORS)]
        for s in c:
            if s:
                pts = " ".join(f"{x(a):.1f},{y(b):.1f}" for a, b in zip(*s))
                o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-opacity="0.3" stroke-width="1"/>')
        if c and all(c):
            n_pts = min(len(s[0]) for s in c)
            mean = [st.fmean(s[1][k] for s in c) for k in range(n_pts)]
            pts = " ".join(f"{x(c[0][0][k]):.1f},{y(mean[k]):.1f}" for k in range(n_pts))
            o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2"/>')
        o.append(f'<line x1="{W - R + 12}" x2="{W - R + 32}" y1="{T + 10 + 18 * i}" y2="{T + 10 + 18 * i}" stroke="{col}" stroke-width="3"/>')
        o.append(f'<text x="{W - R + 38}" y="{T + 14 + 18 * i}">{n}</text>')
    o.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#444"/></svg>')
    write(path, "\n".join(o))


# ---- build -----------------------------------------------------------------------------------------------------------
def build(camp, quiet=False):
    plan, machine, runs = load(camp)
    names = [n for n in plan["selected_configs"] if any(r["config"] == n for r in runs)]
    by = {n: [r for r in runs if r["config"] == n] for n in names}
    stats = {n: {k: describe([r["metrics"].get(k) for r in rs if r["metrics"]]) for k in METRICS} for n, rs in by.items()}
    verdict, checks, suggest = verify(plan, runs)
    vv = {**DEFAULT_VERIFY, **plan.get("verify", {})}
    free_stats = {n: {k: describe([r["metrics"].get(k) for r in rs if r["metrics"] and r["event"] == "none (drift)"]) for k in METRICS}
                  for n, rs in by.items()}
    attribution = {n: {e: sum(1 for r in rs if r["metrics"] and r["event"] == e) for e in EVENTS} for n, rs in by.items()}
    versions = next((r["versions"] for r in runs if r.get("versions")), {})
    rtfs = [r["rtf"]["median"] for r in runs if r.get("rtf", {}).get("median")]
    figs = os.path.join(camp, "figures")
    os.makedirs(figs, exist_ok=True)

    # figures
    for k in FIGS:
        lab, unit, _, _ = METRICS[k]
        svg_bars(os.path.join(figs, f"{k}.svg"), lab, unit, names, [[r["metrics"].get(k) for r in by[n] if r["metrics"]] for n in names],
                 ref=vv["performance_horiz_max_m"] if k == "ekf_h_max" else None,
                 hollow=[[r["event"] != "none (drift)" for r in by[n] if r["metrics"]] for n in names])
    for key, lab, unit in (("ekf_horiz_err_m", "EKF2 horizontal error vs ground truth", "m"),
                           ("ev_yaw_err_deg", "ZED yaw error vs ground truth (|.|)", "deg")):
        curves = [[(r["series"]["t_s"], [abs(v) for v in r["series"][key]]) if r["series"] else None for r in by[n]] for n in names]
        svg_series(os.path.join(figs, f"{key}.svg"), lab, unit, names, curves)

    # summary.md
    md = [f"# VIO benchmark `{os.path.basename(camp.rstrip('/'))}`", "",
          f"**Verdict: {verdict}**  (`tests/vio_report.py`; checks below; config `campaign.yaml`)", ""]
    md += ["## Verdict checks", "", "| check | result | value |", "|---|---|---|"]
    md += [f"| {c} | {'PASS' if ok else 'FAIL'} | {val} |" for c, ok, val in checks]
    if suggest:
        md += ["", "Suggested calibration for this machine:"] + [f"- {s}" for s in suggest]
    md += ["", "## Experimental setup", "", "| | |", "|---|---|",
           f"| host | {machine['host']} ({machine['os']}, kernel {machine['kernel']}) |",
           f"| CPU / RAM | {machine['cpu']}, {machine['cpu_threads']} threads / {machine['ram_gb']} GB |",
           f"| GPU (name, VRAM, driver) | {'; '.join(machine['gpus'])} |",
           f"| Docker | {machine['docker']} |",
           f"| repo | {machine['git_branch']} @ {machine['git_commit']}{' (uncommitted changes)' if machine['git_dirty'] else ''}, Pegasus {machine['pegasus_commit']} |",
           f"| images | " + ", ".join(f"{v['image']} ({v['id']})" for k, v in versions.items() if isinstance(v, dict)) + " |",
           f"| Isaac Sim / PX4 / ZED SDK | {versions.get('isaac_sim', '?')} / {versions.get('px4', '?')} / {versions.get('zed_sdk', '?')} |",
           f"| PX4 param files | {versions.get('px4_param_files', '?')} (+ per-config params set live) |",
           f"| scenario / view | {plan.get('scenario')} / {plan['view']} (raptor, ZED Mini SDK twin, LW20, PMW3901, baro) |",
           f"| world | {os.path.basename(versions.get('world') or '?')}" + (f", lights {versions['world_lights']}" if versions.get('world_lights') else "") + (f", ambient {versions['ambient_light']}" if versions.get('ambient_light') else "") + " |",
           f"| sim real-time factor in flight | " + (f"median {st.median(rtfs):.2f} (min {min(rtfs):.2f}, max {max(rtfs):.2f})" if rtfs else "-") + " |",
           f"| design | {len(names)} configs x {plan['reps']} flights, interleaved per repetition, fresh sim per flight, ZED fused before takeoff |",
           f"| profile | tests/vio_bench.py {plan.get('flight_args', '')}: 20 s hover, altitude steps 0.6/2.0/1.2 m, ±1.5 m legs at 0.5 and 1 m/s, four 90° yaw steps, yawed legs, 1.5 m square, 20 s hover, OFFBOARD landing (~130 s airborne, ~26 m path) |",
           f"| ground truth | Pegasus state -> PX4 `*_groundtruth` (same clock as EKF2); errors are displacements from takeoff |", ""]
    md += ["Configs:", "", "| config | params set live | what it tests |", "|---|---|---|"]
    md += [f"| `{n}` | {', '.join(f'{k}={v:g}' for k, v in (plan['configs'][n]['params'] or {}).items()) or '-'} | {plan['configs'][n]['about']} |"
           for n in names]
    md += ["", "## Results (mean ± std (min-max) over the flights of each config)", "",
           "| config | flights | pass | " + " | ".join(f"{METRICS[k][0]} [{METRICS[k][1]}]" for k in TABLE) + " |",
           "|---|---|---|" + "---|" * len(TABLE)]
    for n in names:
        rs = by[n]
        done = [r for r in rs if r.get("status") == "done"]
        md.append(f"| `{n}` | {len(done)}/{len(rs)} | {sum(r['passed'] for r in done)}/{len(done)} | "
                  + " | ".join(fmt(stats[n][k], METRICS[k][2]) for k in TABLE) + " |")
    lim = vv["performance_horiz_max_m"]
    md += ["", f"## Performance and failure attribution (EKF2 horizontal max <= {lim} m; dominant SDK event per flight, tests/vio_eval.py)", "",
           f"| config | flights | within {lim} m | " + " | ".join(EVENTS) + " | EKF2 h max, event-free flights [m] | EKF2 h max, flights with an event [m] |",
           "|---|---|---|" + "---|" * len(EVENTS) + "---|---|"]
    for n in names:
        fl = [r for r in by[n] if r["metrics"]]
        ev_vals = [r["metrics"]["ekf_h_max"] for r in fl if r["event"] != "none (drift)"]
        md.append(f"| `{n}` | {len(fl)} | {sum(r['metrics']['ekf_h_max'] <= lim for r in fl)}/{len(fl)} | "
                  + " | ".join(str(attribution[n][e]) for e in EVENTS) + f" | {fmt(free_stats[n]['ekf_h_max'], 3)} | {fmt(describe(ev_vals), 3)} |")
    tot = {e: sum(a[e] for a in attribution.values()) for e in EVENTS}
    nfl = sum(1 for r in runs if r["metrics"])
    md += ["", f"All configs: {nfl} flights, " + ", ".join(f"{e}: {c}" for e, c in tot.items()) + ". An event is an SDK tracking failure of the "
           "IMU-less sim ZED (docs/vio.md); the event-free column isolates what the parameters do."]
    if "calibrated" in names:
        md += ["", "## Ablation: difference of the means vs `calibrated` (positive = worse for errors)", "",
               "| config | " + " | ".join(f"Δ {METRICS[k][0]} [{METRICS[k][1]}]" for k in TABLE[:7]) + " |", "|---|" + "---|" * 7]
        base = stats["calibrated"]
        for n in names:
            if n == "calibrated":
                continue
            cells = []
            for k in TABLE[:7]:
                a, b = stats[n][k], base[k]
                cells.append(f"{a['mean'] - b['mean']:+.{METRICS[k][2]}f}" if a.get("n") and b.get("n") else "-")
            md.append(f"| `{n}` | " + " | ".join(cells) + " |")
        md += ["", "Event-free flights only (the parameter effect without the SDK events): EKF2 horizontal max / RMS, ZED yaw end:", "",
               "| config | n | EKF2 h max [m] | EKF2 h RMS [m] | ZED yaw end [deg] | worst yaw slip per rotation [deg] |", "|---|---|---|---|---|---|"]
        for n in names:
            fs = free_stats[n]
            md.append(f"| `{n}` | {fs['ekf_h_max'].get('n', 0)} | {fmt(fs['ekf_h_max'], 3)} | {fmt(fs['ekf_h_rms'], 3)} | "
                      f"{fmt(fs['ev_yaw_end'], 2)} | {fmt(fs['yaw_step_worst'], 2)} |")
    md += ["", "## Calibration of the ZED pipeline (every flight; independent of the EKF2 params)", "",
           "| quantity | all flights | what it calibrates |", "|---|---|---|"]
    allm = {k: describe([r["metrics"].get(k) for r in runs if r["metrics"]]) for k in METRICS}
    what = {"latency": "zed.yaml sim `restamp_latency_ms` (residual should be ~0)", "vel_scale_x": "velocity frame/scale (1.0)",
            "vel_scale_y": "velocity frame/scale (1.0)", "vel_rmse": "vs `EKF2_EVV_NOISE` 0.1 m/s",
            "lever_fit": "`EKF2_EV_POS_*` (raptor.params) (~0; from the hover yaw steps)", "pos_noise": "vs `EKF2_EVP_NOISE` 0.1 m"}
    md += [f"| {METRICS[k][0]} [{METRICS[k][1]}] | {fmt(allm[k], METRICS[k][2] + 1)} | {what[k]} |" for k in CALIB]
    infra = [(r["dir"], f) for r in runs for f in r.get("infra_failures", [])]
    md += ["", "## Reliability of the sim stack", "",
           f"{len(infra)} infra failure(s) over {sum(r.get('attempts', len(r.get('infra_failures', []))) for r in runs)} boots "
           f"(each retried on a fresh sim; not counted against the VIO):", ""]
    md += [f"- `{d}` attempt {f['attempt']}: {f['what']}" for d, f in infra] or ["- none"]
    md += ["", "## Flights", "", "| flight | status | attempts | RTF | flight | gates | EKF2 h max [m] | ZED yaw end [deg] | gaps | dominant event | fails |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        m = r["metrics"]
        md.append(f"| `{r['dir']}` | {r.get('status')} | {r.get('attempts', '-')} | {r.get('rtf', {}).get('median', '-')} | "
                  f"{'ok' if r.get('flight_rc') == 0 else r.get('flight_rc', '-')} | {'PASS' if r['passed'] else 'FAIL'} | "
                  f"{m.get('ekf_h_max', float('nan')):.3f} | {m.get('ev_yaw_end', float('nan')):.2f} | {m.get('gaps', float('nan')):.0f} | {r['event']} | "
                  f"{'; '.join((r['eval'] or {}).get('fails', [])) or '-'} |")
    md += ["", "## Figures", ""] + [f"![{METRICS[k][0]}](figures/{k}.svg)" for k in FIGS] + \
          ["![EKF2 horizontal error over time](figures/ekf_horiz_err_m.svg)", "![ZED yaw error over time](figures/ev_yaw_err_deg.svg)", ""]
    write(os.path.join(camp, "summary.md"), "\n".join(md))

    # summary.json / .csv
    write(os.path.join(camp, "summary.json"), json.dumps({"verdict": verdict, "checks": [{"check": c, "pass": ok, "value": v} for c, ok, v in checks], "suggestions": suggest,
               "machine": machine, "versions": versions, "stats": stats, "stats_event_free": free_stats, "attribution": attribution,
               "all_flights": allm,
               "flights": [{k: r.get(k) for k in ("dir", "config", "rep", "status", "attempts", "flight_rc", "rtf", "passed", "event", "metrics",
                                                  "infra_failures", "params_applied")} for r in runs]}, indent=1))
    with open(os.path.join(camp, "summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["flight", "config", "rep", "status", "attempts", "rtf", "passed", "event"] + list(METRICS))
        for r in runs:
            w.writerow([r["dir"], r["config"], r.get("rep"), r.get("status"), r.get("attempts"), r.get("rtf", {}).get("median"),
                        int(r["passed"]), r["event"]] + [r["metrics"].get(k, "") for k in METRICS])
    if not quiet:
        print(f"{camp}/summary.md: verdict {verdict}")
        for c, ok, v in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {c}: {v}")
        for s in suggest:
            print(f"  suggest: {s}")
    return verdict


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: vio_report.py <campaign dir>")
    v = build(sys.argv[1])
    sys.exit({"PASS": 0, "FAIL": 1}.get(v, 2))
