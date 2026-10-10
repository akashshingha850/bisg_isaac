#!/usr/bin/env python3
"""
Analysis of the ZED pool-depth probe (sim/tools/zed_pool_probe.py + tests/zed_pool_probe_collect.py), numpy only.

Each recorded SDK depth frame is assigned to the view whose dwell window contains its receive time, then compared with
that view's ground truth AND the previous view's, so a frame still showing the old pose ("stale") is told apart from a
fresh one. Per view: time to the first fresh frame and to the first settled one (error within 1.5x of the view's final
error); overall: accuracy of settled frames by depth, valid-pixel coverage, and repeatability on revisited views.

    python3 tests/zed_pool_probe_eval.py sim/cache/zprobe [--out report.json]
"""
import argparse
import json
import os

import numpy as np


def frame_err(sdk, gt, dmin, dmax):
    m = np.isfinite(gt) & (gt > dmin) & (gt < dmax)
    ok = m & np.isfinite(sdk) & (sdk > 0)
    if m.sum() == 0:
        return None
    rel = np.abs(sdk[ok] - gt[ok]) / gt[ok]
    return {"valid": float(ok.sum() / m.sum()), "rel_med": float(np.median(rel)) if rel.size else np.nan,
            "rel_p90": float(np.percentile(rel, 90)) if rel.size else np.nan,
            "abs_med_m": float(np.median(np.abs(sdk[ok] - gt[ok]))) if rel.size else np.nan,
            "inlier5": float(np.mean(rel < 0.05)) if rel.size else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--dmin", type=float, default=0.3)
    ap.add_argument("--dmax", type=float, default=15.0)
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.dir, "views.json")))
    z = np.load(os.path.join(a.dir, "sdk_depth.npz"))
    depth, t_recv, s = z["depth"].astype(np.float32), z["t_recv"], int(z["stride"])
    views = meta["views"]
    gts = [np.load(os.path.join(a.dir, f"gt_{i:03d}.npy"))[::s, ::s] for i in range(len(views))]
    t_tp = [v["t_teleport"] for v in views] + [meta["t_done"] + 1.0]

    per_view, settled = [], []
    for i, v in enumerate(views):
        idx = np.flatnonzero((t_recv >= t_tp[i]) & (t_recv < t_tp[i + 1]))
        rows = []
        for j in idx:
            cur = frame_err(depth[j], gts[i], a.dmin, a.dmax)
            prev = frame_err(depth[j], gts[i - 1], a.dmin, a.dmax) if i > 0 else None
            rows.append({"dt": float(t_recv[j] - t_tp[i]), **cur,
                         "stale": bool(prev is not None and prev["rel_med"] < cur["rel_med"])})
        if not rows:
            per_view.append({"view": i, "frames": 0})
            continue
        final = np.median([r["rel_med"] for r in rows[-3:]])
        fresh = next((r for r in rows if not r["stale"]), None)
        good = next((r for r in rows if not r["stale"] and r["rel_med"] <= 1.5 * final + 1e-3), None)
        if good is not None:
            settled += [(i, j, r) for j, r in zip(idx, rows) if r["dt"] >= good["dt"]]
        per_view.append({"view": i, "revisit": bool(v.get("revisit")), "frames": len(rows),
                         "stale_frames": sum(r["stale"] for r in rows),
                         "first_fresh_s": fresh["dt"] if fresh else None, "settled_s": good["dt"] if good else None,
                         "final_rel_med": float(final), "final_valid": float(np.median([r["valid"] for r in rows[-3:]]))})

    # accuracy of settled frames by ground-truth depth
    bins = [(0.3, 2), (2, 5), (5, 10), (10, 15)]
    by_depth = []
    for lo, hi in bins:
        rel, cov = [], []
        for i, j, _ in settled:
            gt, d = gts[i], depth[j]
            m = np.isfinite(gt) & (gt > lo) & (gt < hi)
            ok = m & np.isfinite(d) & (d > 0)
            if m.sum():
                cov.append(ok.sum() / m.sum())
                rel.append(np.abs(d[ok] - gt[ok]) / gt[ok])
        if rel:
            r = np.concatenate(rel)
            by_depth.append({"depth_m": f"{lo:g}-{hi:g}", "pixels": int(r.size), "valid": float(np.mean(cov)),
                             "rel_med": float(np.median(r)), "rel_p90": float(np.percentile(r, 90)),
                             "inlier5": float(np.mean(r < 0.05))})

    # repeatability: the same pose visited twice (revisit views repeat the first N)
    rep = []
    n_rev = sum(1 for v in views if v.get("revisit"))
    for k in range(n_rev):
        i1, i2 = k, len(views) - n_rev + k
        last = lambda i: [j for (vi, j, _) in settled if vi == i][-3:]   # noqa: E731
        a1, a2 = last(i1), last(i2)
        if a1 and a2:
            d1, d2 = np.median(depth[a1], axis=0), np.median(depth[a2], axis=0)
            m = np.isfinite(d1) & np.isfinite(d2) & (d1 > 0) & (d2 > 0)
            rep.append(float(np.median(np.abs(d1[m] - d2[m]) / d1[m])))

    fresh = [p["first_fresh_s"] for p in per_view if p.get("first_fresh_s") is not None]
    sett = [p["settled_s"] for p in per_view if p.get("settled_s") is not None]
    allrel = [r["rel_med"] for _, _, r in settled]
    report = {
        "views": len(views), "sdk_frames": int(len(t_recv)),
        "sdk_rate_hz": float(len(t_recv) / (t_recv[-1] - t_recv[0])) if len(t_recv) > 1 else 0.0,
        "dwell_s_median": float(np.median(np.diff(t_tp[:-1]))),
        "first_fresh_s": {"median": float(np.median(fresh)), "max": float(np.max(fresh))} if fresh else None,
        "settled_s": {"median": float(np.median(sett)), "max": float(np.max(sett))} if sett else None,
        "views_settled": len(sett),
        "settled_rel_med": float(np.median(allrel)) if allrel else None,
        "settled_valid_med": float(np.median([r["valid"] for _, _, r in settled])) if settled else None,
        "by_depth": by_depth, "revisit_rel_diff_med": rep, "per_view": per_view,
    }
    print(json.dumps({k: v for k, v in report.items() if k != "per_view"}, indent=1))
    print("view frames stale first_fresh_s settled_s final_rel_med final_valid")
    for p in per_view:
        print(p["view"], p.get("frames"), p.get("stale_frames"), p.get("first_fresh_s"), p.get("settled_s"),
              round(p.get("final_rel_med", np.nan), 4), round(p.get("final_valid", np.nan), 3))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
