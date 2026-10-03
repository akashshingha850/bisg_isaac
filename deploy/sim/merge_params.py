#!/usr/bin/env python3
"""Deep-merge ROS 2 parameter YAMLs: merge_params.py out.yaml base.yaml overlay.yaml [...].

zed_wrapper takes ONE `ros_params_override_path`. In sim we want the hardware params (deploy/jetson/zed_params.yaml)
plus a few sim-only lines (deploy/sim/zed_sim_overlay.yaml) without keeping a second copy of the hardware file.
"""
import sys

import yaml


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


out, *srcs = sys.argv[1:]
cfg = {}
for path in srcs:
    with open(path) as fh:
        cfg = merge(cfg, yaml.safe_load(fh) or {})
with open(out, "w") as fh:
    yaml.safe_dump(cfg, fh, sort_keys=False)
print(f"merged {len(srcs)} files -> {out}")
