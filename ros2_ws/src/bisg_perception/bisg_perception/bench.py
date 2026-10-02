"""
bench: score a perception backend on the sim's own ground truth while a flight runs (docs/perception.md).

Runs in the /drone_<n> namespace next to a backend (perception.launch.py) and a flight (tests/vio_flight.py). It only
listens, so every backend is judged on the same trajectory.

Odometry  perception/odom vs state/pose (Pegasus ground truth; test-only, parity rule plan.md §8)
          ATE RMSE after rigid alignment (Umeyama, with and without scale), origin-aligned RMSE and end-point drift,
          output rate, latency.
Depth     perception/disparity (-> depth = f*T/d) vs zed/zed_node/depth/depth_registered (exact sim depth), matched by
          header stamp, over pixels the sim sees between --near and --far: coverage, MAE, median |err|, RMSE, relative error.
Timing    everything is stamped on the SIM clock; wall figures divide by the measured real-time factor (sim s per wall s).
          Latency = sim arrival time - header stamp (so DDS + processing, as seen by a consumer).

Ends when the flight is over (altitude went above --min-alt and back under 0.3 m) or after --max-wall seconds, then writes
JSON to --out-dir and prints a summary.
"""
import json
import math
import os
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image
from stereo_msgs.msg import DisparityImage


def img_array(msg: Image):
    """float32 (h, w) from a 32FC1 Image, honouring the row stride."""
    row = msg.step // 4
    a = np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, row)
    return a[:, :msg.width]


def pct(v, q):
    return float(np.percentile(v, q)) if len(v) else float("nan")


def umeyama(est, gt, with_scale):
    """Rigid (optionally similarity) alignment of est onto gt. Returns aligned est and the scale."""
    mu_e, mu_g = est.mean(0), gt.mean(0)
    e, g = est - mu_e, gt - mu_g
    cov = g.T @ e / len(est)
    u, d, vt = np.linalg.svd(cov)
    s = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s[2, 2] = -1
    r = u @ s @ vt
    scale = float(np.trace(np.diag(d) @ s) / (e ** 2).sum(1).mean()) if with_scale else 1.0
    return (scale * (r @ e.T)).T + mu_g, scale


class Bench(Node):
    def __init__(self):
        super().__init__("bench")
        d = self.declare_parameter
        d("backend", "unknown"); d("max_wall_s", 300.0); d("min_alt", 1.5); d("near", 0.5); d("far", 6.0)
        d("out_dir", "/workspace/logs/perception"); d("tag", "")
        gp = lambda n: self.get_parameter(n).value  # noqa: E731
        self.backend, self.max_wall, self.min_alt = str(gp("backend")), float(gp("max_wall_s")), float(gp("min_alt"))
        self.near, self.far, self.out_dir, self.tag = float(gp("near")), float(gp("far")), str(gp("out_dir")), str(gp("tag"))

        self.t_wall0 = time.monotonic()
        self.sim_now = 0.0
        self.clock_pairs = []            # (wall, sim) every ~0.5 s wall
        self._last_pair = 0.0
        self.gt_t, self.gt_p = [], []    # arrival sim time, xyz
        self.z_max, self.z_now, self.flight_done_at = 0.0, 0.0, None
        self.odom = []                   # (stamp, xyz, arrival_sim, arrival_wall)
        self.depth_frames = {}           # stamp_ns -> gt depth array (ring)
        self.in_wall = {}                # stamp_ns -> wall arrival of the input frame (ring), for wall-time latency
        self.depth_in = []               # (stamp, arrival_wall)
        self.disp = []                   # per-frame dict
        self.mismatch = 0
        self.t_convention = "?"
        self.frames_dumped = 0

        self.create_subscription(Clock, "/clock", self._on_clock, 10)
        self.create_subscription(PoseStamped, "state/pose", self._gt, qos_profile_sensor_data)
        self.create_subscription(Odometry, "perception/odom", self._odom, qos_profile_sensor_data)
        self.create_subscription(Image, "zed/zed_node/depth/depth_registered", self._depth, qos_profile_sensor_data)
        self.create_subscription(DisparityImage, "perception/disparity", self._disp, qos_profile_sensor_data)
        self.create_timer(1.0, self._tick)
        self.get_logger().info(f"bench: backend={self.backend}, waiting for a flight (alt > {self.min_alt} m, then landing)")

    # ---- inputs ----------------------------------------------------------------------------------------------------
    def _on_clock(self, m: Clock):
        self.sim_now = m.clock.sec + m.clock.nanosec * 1e-9
        w = time.monotonic()
        if w - self._last_pair > 0.5:
            self._last_pair = w
            self.clock_pairs.append((w, self.sim_now))

    def _gt(self, m: PoseStamped):
        p = m.pose.position
        self.gt_t.append(self.sim_now)
        self.gt_p.append((p.x, p.y, p.z))
        self.z_now = p.z
        self.z_max = max(self.z_max, p.z)
        if self.z_max > self.min_alt and p.z < 0.3 and self.flight_done_at is None:
            self.flight_done_at = time.monotonic()

    def _odom(self, m: Odometry):
        p = m.pose.pose.position
        w = time.monotonic()
        key = m.header.stamp.sec * 10 ** 9 + m.header.stamp.nanosec
        self.odom.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, (p.x, p.y, p.z), self.sim_now, w, self._lat_wall(key, w)))

    def _lat_wall(self, key, wall_out):
        """Wall seconds from the input frame reaching this node to the backend's output reaching it (± DDS)."""
        for k in (key, key - 1_000_000, key + 1_000_000):
            w = self.in_wall.get(k)
            if w is not None:
                return wall_out - w
        return None

    def _depth(self, m: Image):
        key = m.header.stamp.sec * 10 ** 9 + m.header.stamp.nanosec
        self.in_wall[key] = time.monotonic()
        while len(self.in_wall) > 64:
            self.in_wall.pop(next(iter(self.in_wall)))
        self.depth_frames[key] = img_array(m).copy()
        self.depth_in.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, time.monotonic()))
        while len(self.depth_frames) > 16:
            self.depth_frames.pop(next(iter(self.depth_frames)))

    def _disp(self, m: DisparityImage):
        arrive_sim, arrive_wall = self.sim_now, time.monotonic()
        stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        key = m.header.stamp.sec * 10 ** 9 + m.header.stamp.nanosec
        gt = None
        for k in (key, key - 1_000_000, key + 1_000_000):
            gt = self.depth_frames.get(k)
            if gt is not None:
                break
        rec = {"lat_sim": arrive_sim - stamp, "wall": arrive_wall, "matched": gt is not None, "lat_wall": self._lat_wall(key, arrive_wall)}
        if gt is not None:
            d = img_array(m.image)
            if d.shape != gt.shape:
                self.mismatch += 1
            else:
                # DisparityImage.t is the baseline in metres in stereo_image_proc; Isaac ROS fills it with -P[0,3] = fx*baseline
                # (pixels*metres). Normalise: any t above 1 is not a metre baseline of a ZED-class rig.
                base = m.t / m.f if m.t > 1.0 else m.t
                self.t_convention = "t = fx*baseline (Isaac ROS)" if m.t > 1.0 else "t = baseline [m] (stereo_image_proc)"
                dmax = m.max_disparity if m.max_disparity > 0 else float("inf")
                with np.errstate(divide="ignore", invalid="ignore"):
                    est = (m.f * base) / d
                ok_gt = np.isfinite(gt) & (gt > self.near) & (gt < self.far)
                ok_est = np.isfinite(est) & (d > 0.5) & (d <= dmax) & (est > 0.0)
                both = ok_gt & ok_est
                n_gt = int(ok_gt.sum())
                bins = {}
                for lo, hi in ((0.5, 1.5), (1.5, 3.0), (3.0, 6.0)):
                    sel = ok_gt & (gt >= lo) & (gt < hi)
                    sel_ok = sel & ok_est
                    if sel.sum() > 50:
                        r_ = est[sel_ok] / gt[sel_ok] if sel_ok.any() else np.array([])
                        bins[f"{lo}-{hi}"] = {"cov": float(sel_ok.sum() / sel.sum()),
                                              "bias_ratio": float(np.median(r_)) if r_.size else float("nan"),
                                              "medae": float(np.median(np.abs(est[sel_ok] - gt[sel_ok]))) if r_.size else float("nan")}
                rec["bins"] = bins
                if self.frames_dumped < 1 and n_gt > 1000 and self.z_now > 1.0:
                    self.frames_dumped += 1
                    os.makedirs(self.out_dir, exist_ok=True)
                    np.savez_compressed(os.path.join(self.out_dir, f"{self.backend}{('_' + self.tag) if self.tag else ''}_frame.npz"),
                                        gt=gt, est=est.astype(np.float32), disp=d, f=m.f, t=m.t, max_disp=m.max_disparity)
                if n_gt:
                    err = np.abs(est[both] - gt[both])
                    rec.update(coverage=float(both.sum() / n_gt), n=int(both.sum()))
                    if err.size:
                        rec.update(mae=float(err.mean()), medae=float(np.median(err)), rmse=float(math.sqrt((err ** 2).mean())),
                                   rel=float(np.median(err / gt[both])))
        self.disp.append(rec)

    # ---- end of run ------------------------------------------------------------------------------------------------
    def _tick(self):
        now = time.monotonic()
        if now - self.t_wall0 > self.max_wall or (self.flight_done_at and now - self.flight_done_at > 2.0):
            self._finish("timeout" if now - self.t_wall0 > self.max_wall else "flight over")

    def _rtf(self):
        if len(self.clock_pairs) < 2:
            return float("nan")
        (w0, s0), (w1, s1) = self.clock_pairs[0], self.clock_pairs[-1]
        return (s1 - s0) / (w1 - w0) if w1 > w0 else float("nan")

    def _rate(self, arrivals_wall, rtf):
        if len(arrivals_wall) < 3:
            return float("nan"), float("nan")
        hz = (len(arrivals_wall) - 1) / (arrivals_wall[-1] - arrivals_wall[0])
        return hz, hz / rtf if rtf > 0 else float("nan")

    def _finish(self, why):
        rtf = self._rtf()
        res = {"backend": self.backend, "tag": self.tag, "ended": why, "rtf": rtf,
               "wall_s": time.monotonic() - self.t_wall0, "gt_samples": len(self.gt_t), "z_max": self.z_max}

        # odometry
        o = {"frames": len(self.odom)}
        if len(self.odom) >= 10 and len(self.gt_t) >= 10:
            t_gt, p_gt = np.array(self.gt_t), np.array(self.gt_p)
            stamps = np.array([x[0] for x in self.odom])
            est = np.array([x[1] for x in self.odom])
            idx = np.clip(np.searchsorted(t_gt, stamps), 0, len(t_gt) - 1)
            keep = np.abs(t_gt[idx] - stamps) < 0.05
            est, gt = est[keep], p_gt[idx[keep]]
            if len(est) >= 10:
                self._traj = np.hstack([stamps[keep][:, None], est, gt])   # t, est xyz (backend frame), gt xyz (world)
                aligned, _ = umeyama(est, gt, False)
                aligned_s, scale = umeyama(est, gt, True)
                shift = gt[:5].mean(0) - est[:5].mean(0)
                origin = est + shift
                path = float(np.linalg.norm(np.diff(gt, axis=0), axis=1).sum())
                o.update(matched=int(len(est)),
                         ate_rmse_m=float(math.sqrt(((aligned - gt) ** 2).sum(1).mean())),
                         ate_rmse_scaled_m=float(math.sqrt(((aligned_s - gt) ** 2).sum(1).mean())), scale=scale,
                         origin_rmse_m=float(math.sqrt(((origin - gt) ** 2).sum(1).mean())),
                         origin_max_m=float(np.linalg.norm(origin - gt, axis=1).max()),
                         end_drift_m=float(np.linalg.norm(origin[-1] - gt[-1])), gt_path_m=path)
        hz_w, hz_s = self._rate([x[3] for x in self.odom], rtf)
        lat = np.array([x[2] - x[0] for x in self.odom]) if self.odom else np.array([])
        lw = np.array([x[4] for x in self.odom if x[4] is not None])
        o.update(rate_hz_wall=hz_w, rate_hz_sim=hz_s, lat_sim_ms_p50=pct(lat, 50) * 1e3, lat_sim_ms_p95=pct(lat, 95) * 1e3,
                 lat_wall_ms_p50=pct(lw, 50) * 1e3, lat_wall_ms_p95=pct(lw, 95) * 1e3, lat_wall_n=int(len(lw)))
        res["odometry"] = o

        # depth
        dd = {"frames": len(self.disp), "matched": sum(1 for r in self.disp if r["matched"]), "shape_mismatch": self.mismatch}
        good = [r for r in self.disp if "mae" in r]
        for k in ("coverage", "mae", "medae", "rmse", "rel"):
            vals = [r[k] for r in good if k in r]
            dd[k] = float(np.mean(vals)) if vals else float("nan")
        hz_w, hz_s = self._rate([r["wall"] for r in self.disp], rtf)
        lat = np.array([r["lat_sim"] for r in self.disp]) if self.disp else np.array([])
        lw = np.array([r["lat_wall"] for r in self.disp if r.get("lat_wall") is not None])
        dd.update(rate_hz_wall=hz_w, rate_hz_sim=hz_s, lat_sim_ms_p50=pct(lat, 50) * 1e3, lat_sim_ms_p95=pct(lat, 95) * 1e3,
                  lat_wall_ms_p50=pct(lw, 50) * 1e3, lat_wall_ms_p95=pct(lw, 95) * 1e3, lat_wall_n=int(len(lw)),
                  disparity_t_convention=self.t_convention)
        agg = {}
        for r in good:
            for k, v in r.get("bins", {}).items():
                agg.setdefault(k, {"cov": [], "bias_ratio": [], "medae": []})
                for kk in ("cov", "bias_ratio", "medae"):
                    if v[kk] == v[kk]:
                        agg[k][kk].append(v[kk])
        dd["by_range_m"] = {k: {kk: (float(np.mean(vv)) if vv else float("nan")) for kk, vv in v.items()} for k, v in agg.items()}
        res["depth"] = dd
        res["input_depth_rate_hz_sim"] = self._rate([x[1] for x in self.depth_in], rtf)[1]

        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, f"{self.backend}{('_' + self.tag) if self.tag else ''}_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w") as f:
            json.dump(res, f, indent=2)
        if getattr(self, "_traj", None) is not None:
            np.savetxt(path[:-5] + ".traj.csv", self._traj, delimiter=",", header="t,est_x,est_y,est_z,gt_x,gt_y,gt_z", comments="")
        self.get_logger().info("bench result:\n" + json.dumps(res, indent=2) + f"\nsaved {path}")
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = Bench()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
