#!/usr/bin/env python3
"""Run every ZED SDK configuration of the study on one SVO, N repeats each, one process per run (clean CUDA state).

    scripts/study_run.sh python3 tests/study/run_matrix.py --svo logs/study/d1/flight.svo2 --out logs/study/results/d1 [--repeats 3] [--only name,...]
Skips runs whose summary.json already exists, so an interrupted matrix resumes.
"""
import argparse
import json
import os
import subprocess
import sys

# name -> svo_bench.py arguments. Baseline = GEN_3, NEURAL_LIGHT, SDK defaults for everything else.
M = {
    # tracking generation x depth mode
    "decode_only": "--tracking NONE --depth NONE",
    "g3_none": "--tracking GEN_3 --depth NONE",
    "g3_perf": "--tracking GEN_3 --depth PERFORMANCE",
    "g3_qual": "--tracking GEN_3 --depth QUALITY",
    "g3_ultra": "--tracking GEN_3 --depth ULTRA",
    "g3_nl": "--tracking GEN_3 --depth NEURAL_LIGHT",
    "g3_n": "--tracking GEN_3 --depth NEURAL",
    "g3_np": "--tracking GEN_3 --depth NEURAL_PLUS",
    "g1_perf": "--tracking GEN_1 --depth PERFORMANCE",
    "g1_ultra": "--tracking GEN_1 --depth ULTRA",
    "g1_nl": "--tracking GEN_1 --depth NEURAL_LIGHT",
    "g1_n": "--tracking GEN_1 --depth NEURAL",
    "g1_np": "--tracking GEN_1 --depth NEURAL_PLUS",
    "g2_nl": "--tracking GEN_2 --depth NEURAL_LIGHT",
    # tracking options on the lightest tracking set-up (GEN_3, no depth) and on the baseline
    "g3_none_area": "--tracking GEN_3 --depth NONE --area-memory",
    "g3_none_smooth": "--tracking GEN_3 --depth NONE --pose-smoothing",
    "g3_none_noenh": "--tracking GEN_3 --depth NONE --no-image-enhancement",
    "g3_none_fps15": "--tracking GEN_3 --depth NONE --fps-cap 15",
    "g3_none_fps10": "--tracking GEN_3 --depth NONE --fps-cap 10",
    "g3_none_fps5": "--tracking GEN_3 --depth NONE --fps-cap 5",
    "g1_nl_fps15": "--tracking GEN_1 --depth NEURAL_LIGHT --fps-cap 15",
    # depth options on the baseline depth mode
    # cuVSLAM (NVIDIA) stereo, no IMU, on the same frames (cuvslam_bench.py)
    "cu_prec": "CU --mode Precision",
    "cu_mod": "CU --mode Moderate",
    "cu_perf": "CU --mode Performance",
    "cu_prec_half": "CU --mode Precision --scale 2",
    "cu_perf_half": "CU --mode Performance --scale 2",
    "cu_prec_denoise": "CU --mode Precision --denoise",
    "cu_prec_slam": "CU --mode Precision --slam",
    "cu_prec_fps15": "CU --mode Precision --fps-cap 15",
    "cu_prec_fps10": "CU --mode Precision --fps-cap 10",
    "cu_prec_cpu": "CU --mode Precision --no-gpu",
    "cu_mod_noise5": "CU --mode Moderate --noise 5",
    "cu_mod_noise15": "CU --mode Moderate --noise 15",
    "cu_mod_blur5": "CU --mode Moderate --blur 5",
    "cu_mod_dark": "CU --mode Moderate --gain 0.35 --noise 5",
    "cu_prec_noise5": "CU --mode Precision --noise 5",
    "cu_prec_blur5": "CU --mode Precision --blur 5",
    "nl_stab0": "--tracking NONE --depth NEURAL_LIGHT --depth-stab 0",
    "nl_stab100": "--tracking NONE --depth NEURAL_LIGHT --depth-stab 100",
    "nl_fill": "--tracking NONE --depth NEURAL_LIGHT --fill-mode",
    "nl_conf50": "--tracking NONE --depth NEURAL_LIGHT --confidence 50",
    "nl_only": "--tracking NONE --depth NEURAL_LIGHT",
    "n_only": "--tracking NONE --depth NEURAL",
    "np_only": "--tracking NONE --depth NEURAL_PLUS",
    "perf_only": "--tracking NONE --depth PERFORMANCE",
    "qual_only": "--tracking NONE --depth QUALITY",
    "ultra_only": "--tracking NONE --depth ULTRA",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    names = [n for n in M if not a.only or n in a.only.split(",")]
    for name in names:
        for r in range(a.repeats):
            out = os.path.join(a.out, f"{name}_r{r}")
            if os.path.exists(os.path.join(out, "summary.json")):
                continue
            if M[name].startswith("CU "):
                cmd = f"python3 tests/study/cuvslam_bench.py --svo {a.svo} --out {out} {M[name][3:]}"
                env = dict(os.environ, PYTHONPATH="/workspace/logs/study/pylib")
            else:
                cmd = f"python3 tests/study/svo_bench.py --svo {a.svo} --out {out} {M[name]} --depth-every 30"
                env = None
            print(">>", name, r, flush=True)
            p = subprocess.run(cmd.split(), capture_output=True, text=True, env=env)
            if p.returncode != 0 or not os.path.exists(os.path.join(out, "summary.json")):
                os.makedirs(out, exist_ok=True)
                with open(os.path.join(out, "FAILED.txt"), "w") as f:
                    f.write(p.stdout[-3000:] + "\n" + p.stderr[-3000:])
                print("   FAILED", p.returncode, (p.stdout + p.stderr)[-300:].replace("\n", " | "), flush=True)
                break                               # a config that cannot run will not run on repeat
            s = json.load(open(os.path.join(out, "summary.json")))
            print(f"   {s['fps_max']:.0f} fps, grab {s['grab_ms_mean']:.1f} ms, gpu {s['gpu_util_mean']:.0f}%, "
                  f"cpu {s['cpu_cores_avg']:.2f} cores, {s['tracking_ok_frames']}/{s['frames_processed']} OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
