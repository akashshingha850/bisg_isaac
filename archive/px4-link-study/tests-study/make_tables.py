#!/usr/bin/env python3
"""Markdown tables for docs/study-vo-perception.md from <run>/analysis/configs.csv + depth_range.csv (stdlib only).
    python3 tests/study/make_tables.py logs/study/d1 > /tmp/tables.md
"""
import csv
import sys

d = sys.argv[1].rstrip("/") + "/analysis/"
C = {r["config"]: r for r in csv.DictReader(open(d + "configs.csv"))}
DEC = float(C["decode_only"]["grab_ms_mean"]) if "decode_only" in C else 0.0
DECCPU = float(C["decode_only"]["cpu_ms_frame"]) if "decode_only" in C else 0.0


def f(r, k, n=2, scale=1.0):
    v = r.get(k, "")
    return "-" if v in ("", None) else f"{float(v) * scale:.{n}f}"


def rng(r, k, n=2):
    return f"{float(r[k + '_min']):.{n}f}-{float(r[k + '_max']):.{n}f}" if r.get(k + "_min") not in ("", None) and r[k + "_min"] != r[k + "_max"] else ""


def row(name, label):
    r = C.get(name)
    if not r:
        return None
    net = max(float(r["grab_ms_mean"]) - (0 if name.startswith("cu_") else DEC), 0.0)
    return (f"| {label} | **{f(r, 'ate_flight')}** {rng(r, 'ate_flight')} | {f(r, 'err_at_land')} | {f(r, 'ate_start')} | {f(r, 'rpe_1s', 3)} | "
            f"{f(r, 'rot_rpe_1s', 1)} | {net:.1f} | {max(float(r['cpu_ms_frame']) - DECCPU, 0):.1f} | {f(r, 'gpu_util', 0)} | {f(r, 'gpu_vram_mib', 0)} |")


H = ("| config | ATE flight [m] | err at landing start [m] | ATE whole run [m] | RPE 1 s [m/m] | rot RPE [deg/s] | pose cost [ms/frame] | CPU [ms/frame] | GPU util % | VRAM [MiB] |\n"
     "|---|---|---|---|---|---|---|---|---|---|")
print("### Pose estimation (one flight, 1872 frames, 39 m path)\n")
print(H)
for n, l in [("cu_perf", "cuVSLAM stereo, Performance"), ("cu_mod", "cuVSLAM stereo, Moderate"), ("cu_prec", "cuVSLAM stereo, Precision"),
             ("cu_prec_slam", "cuVSLAM Precision + SLAM (loop closure)"), ("cu_prec_half", "cuVSLAM Precision, 640x360"),
             ("cu_prec_denoise", "cuVSLAM Precision + denoise"), ("cu_prec_fps15", "cuVSLAM Precision, 15 fps"), ("cu_prec_fps10", "cuVSLAM Precision, 10 fps"),
             ("g1_np", "ZED GEN_1 + NEURAL_PLUS"), ("g1_n", "ZED GEN_1 + NEURAL"), ("g1_nl", "ZED GEN_1 + NEURAL_LIGHT"), ("g1_nl_fps15", "ZED GEN_1 + NEURAL_LIGHT, 15 fps"),
             ("g1_ultra", "ZED GEN_1 + ULTRA"), ("g1_perf", "ZED GEN_1 + PERFORMANCE"),
             ("g3_perf", "ZED GEN_3 + PERFORMANCE/QUALITY/ULTRA*"), ("g3_np", "ZED GEN_3 + NEURAL_PLUS"), ("g3_n", "ZED GEN_3 + NEURAL"), ("g3_nl", "ZED GEN_3 + NEURAL_LIGHT"),
             ("g3_none", "ZED GEN_3, depth off"), ("g3_none_area", "ZED GEN_3, depth off + area memory"), ("g3_none_smooth", "ZED GEN_3 + pose smoothing"),
             ("g3_none_noenh", "ZED GEN_3, image enhancement off"), ("g3_none_fps15", "ZED GEN_3, 15 fps"), ("g3_none_fps10", "ZED GEN_3, 10 fps"), ("g3_none_fps5", "ZED GEN_3, 5 fps"),
             ("g2_nl", "ZED GEN_2 (deprecated) + NEURAL_LIGHT"),
             ("cu_mod_noise5", "cuVSLAM Moderate, noise sigma 5"), ("cu_mod_noise15", "cuVSLAM Moderate, noise sigma 15"), ("cu_mod_blur5", "cuVSLAM Moderate, 5 px blur"),
             ("cu_mod_dark", "cuVSLAM Moderate, 0.35x light + noise 5")]:
    x = row(n, l)
    if x:
        print(x)
print(f"\nPose cost = wall time of the pose call per frame (ZED: grab() minus the {DEC:.1f} ms SVO decode; cuVSLAM: the track() call). CPU = process CPU time per frame minus the {DECCPU:.1f} ms the SVO decode needs. GPU util is measured while replaying as fast as possible, so it shows how GPU-bound a setting is, not its load at 30 fps.")
print("\n*GEN_3 with PERFORMANCE, QUALITY and ULTRA depth gave identical trajectories.\n")

print("### Depth modes (floor-ray depth error: median |error| / true range, % ; share of floor pixels with a valid depth)\n")
D = list(csv.DictReader(open(d + "depth_range.csv")))
bins = []
for r in D:
    if r["bin"] not in bins:
        bins.append(r["bin"])
print("| depth mode | cost [ms/frame] | VRAM [MiB] | " + " | ".join(f"{b} m" for b in bins) + " |\n|---|---|---|" + "---|" * len(bins))
for n, l in [("np_only", "NEURAL_PLUS"), ("n_only", "NEURAL"), ("nl_only", "NEURAL_LIGHT"), ("ultra_only", "ULTRA (legacy)"), ("qual_only", "QUALITY (legacy)"), ("perf_only", "PERFORMANCE (legacy)")]:
    r = C.get(n)
    if not r:
        continue
    cells = []
    for b in bins:
        m = [x for x in D if x["config"] == n and x["bin"] == b]
        cells.append(f"{float(m[0]['med_rel_err_pct']):.1f} ({float(m[0]['valid_frac']):.2f})" if m else "-")
    print(f"| {l} | {float(r['grab_ms_mean']) - DEC:.1f} | {f(r, 'gpu_vram_mib', 0)} | " + " | ".join(cells) + " |")
print(f"\nCost is grab() time minus the {DEC:.1f} ms the SDK needs just to decode the SVO frame (config `decode_only`).\n")
print("### Depth options on NEURAL_LIGHT\n\n| option | cost [ms/frame] | CPU [ms/frame] | note |\n|---|---|---|---|")
for n, l in [("nl_only", "defaults (stabilisation 30?, confidence default)"), ("nl_stab0", "depth_stabilization 0"), ("nl_stab100", "depth_stabilization 100"), ("nl_fill", "fill mode on"), ("nl_conf50", "confidence_threshold 50")]:
    r = C.get(n)
    if r:
        print(f"| {l} | {float(r['grab_ms_mean']) - DEC:.2f} | {max(float(r['cpu_ms_frame']) - DECCPU, 0):.1f} | |")
