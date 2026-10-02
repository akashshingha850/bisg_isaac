#!/usr/bin/env python3
"""Resource sampler for the perception benchmark: run on the host while a backend is processing a flight.

    perception_sample.py OUT.json --stop-file /tmp/x --containers bisg-perception-1,bisg-sim [--period 2]

Every PERIOD seconds records, until the stop file appears: whole-GPU utilisation and memory, per-container CPU % and memory
(docker stats; 100 % = one core) and GPU memory held by the processes of the perception container (nvidia-smi + docker top).
Writes means / p95 / max to OUT.json. Host-side on purpose: the container under test must not run its own measurement load.
"""
import argparse
import json
import os
import statistics
import subprocess
import time


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return ""


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(q / 100 * (len(v) - 1))))] if v else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--containers", default="")
    ap.add_argument("--perception", default="", help="container whose GPU process memory is attributed")
    ap.add_argument("--period", type=float, default=2.0)
    a = ap.parse_args()
    names = [c for c in a.containers.split(",") if c]
    rows = {"gpu_util": [], "gpu_mem_mib": [], "perception_gpu_mem_mib": []}
    for n in names:
        rows[f"{n}.cpu_pct"], rows[f"{n}.mem_mib"] = [], []
    while not os.path.exists(a.stop_file):
        t = time.time()
        g = run("nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits").strip().split(",")
        if len(g) == 2:
            rows["gpu_util"].append(float(g[0])); rows["gpu_mem_mib"].append(float(g[1]))
        for line in run("docker", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}} {{.MemUsage}}", *names).splitlines():
            p = line.split()
            if len(p) >= 3 and p[0] in names:
                rows[f"{p[0]}.cpu_pct"].append(float(p[1].rstrip("%")))
                m, unit = p[2][:-3] if p[2].endswith("iB") else p[2], p[2][-3:-2]
                num = float("".join(ch for ch in p[2].split("/")[0] if ch.isdigit() or ch == "."))
                rows[f"{p[0]}.mem_mib"].append(num * (1024 if "GiB" in p[2].split("/")[0] else 1))
        if a.perception:
            pids = {x.split()[1] for x in run("docker", "top", a.perception, "-eo", "pid,pid").splitlines()[1:] if x.split()}
            tot = 0.0
            for line in run("nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits").splitlines():
                p = [x.strip() for x in line.split(",")]
                if len(p) == 2 and p[0] in pids:
                    tot += float(p[1])
            rows["perception_gpu_mem_mib"].append(tot)
        time.sleep(max(0.0, a.period - (time.time() - t)))
    out = {k: {"mean": statistics.fmean(v) if v else float("nan"), "p95": pct(v, 95), "max": max(v) if v else float("nan"), "n": len(v)}
           for k, v in rows.items()}
    json.dump(out, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
