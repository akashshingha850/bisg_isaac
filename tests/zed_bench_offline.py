#!/usr/bin/env python3
"""Host-side micro-benchmarks of the ZED stack code (no ROS, no GPU, no sim):  python3 tests/zed_bench_offline.py

  config      load + validate + compile docker/zed/zed.yaml (runs at every wrapper start)
  obstacle    depth image -> 72 obstacle sectors, the per-frame cost of the bridge's obstacle_distance module, at HD720 / VGA / 320x180
              (the module runs at <= 10 Hz, so the budget is 100 ms per frame, on ONE core of the Orin NX: compare)
"""
import os
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "docker", "zed"))
from zed_stack import config  # noqa: E402
from zed_stack.bridge.sectors import sectors_from_depth  # noqa: E402


def timeit(fn, n):
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000)
    ts.sort()
    return statistics.mean(ts), ts[int(len(ts) * 0.95) - 1], ts[-1]


def main():
    rows = []
    m = timeit(lambda: config.load(sim=True).wrapper_yaml(), 50)
    rows.append(("config load+validate+compile", "-", *m))
    rng = np.random.default_rng(0)
    for name, (h, w) in {"HD720": (720, 1280), "VGA": (376, 672), "320x180": (180, 320)}.items():
        z = rng.uniform(0.3, 9.0, (h, w)).astype(np.float32)
        z[rng.random((h, w)) < 0.25] = np.nan                       # ~25 % holes like the real depth
        fx = 0.41 * w
        m = timeit(lambda: sectors_from_depth(z, fx, fx, w / 2, h / 2, 0.6, 0.3, 8.0), 100)
        rows.append(("obstacle sectors", f"{name} ({w}x{h})", *m))
    print("| what | input | mean ms | p95 ms | max ms |\n|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:.2f} |")


if __name__ == "__main__":
    main()
