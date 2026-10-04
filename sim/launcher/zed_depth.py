"""
Depth-derived ZED SDK products for the sim ZED Mini, each behind the zed_wrapper switch of the same
name (docker/zed/zed.yaml, see zed_features.py and archive/docs/zed-features.md):

  depth.publish_point_cloud  -> zed/zed_node/point_cloud/cloud_registered  (PointCloud2 x y z rgb,
                                organized, NaN = no depth, frame <ns>/zed_left_camera_frame, x forward)
                                rate depth.point_cloud_freq, resolution depth.point_cloud_res
                                (COMPACT = every 4th pixel, REDUCED = every 8th)
  depth.publish_disparity    -> zed/zed_node/disparity/disparity_image  (stereo_msgs/DisparityImage,
                                d = f*B/Z px, left optical frame)
  mapping.mapping_enabled    -> zed/zed_node/mapping/fused_cloud  (PointCloud2 x y z rgb, voxel grid
                                mapping.resolution, points within mapping.max_mapping_range, frame
                                <ns>/odom = sim world, which is vio_mock's odom), at fused_pointcloud_freq

Topics are published only while something subscribes, like the wrapper. The GUI overlay
(scenario `sensors.zed.view`) draws the live cloud and the fused map over the main viewport with
omni.ui.scene — not isaacsim.util.debug_draw, whose points render into the ZED cameras' own images.

Reads the left camera's render products directly (Camera.get_current_frame), so none of this
depends on the image topics getting through DDS (docs/bugs.md B2). Timestamps are the frame's render
time (sim). The rendered frame lags physics by a frame or two, so the camera pose used to place the
points in the world is looked up at that render time from a short pose history — pairing it with the
*current* pose smeared 11% of the fused map up to ~0.4 m below the floor while banking (2026-09-26).
"""
import bisect
import collections
import logging
import time

import numpy as np

from drone_views import _turbo_lut

LOG = logging.getLogger("launch")
_RES_STRIDE = {"COMPACT": 4, "REDUCED": 8}
_OFF = 1 << 20  # voxel index offset for key packing (±1e6 voxels per axis)


def _quat_wxyz_to_matrix(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def _pack_rgb(c):
    c = c.astype(np.uint32)
    return ((c[..., 0] << 16) | (c[..., 1] << 8) | c[..., 2]).astype(np.uint32)


class ZedDepthProducts:
    def __init__(self, rig: dict, ns: str, zed_cfg: dict, features, sim_time, has_ui: bool):
        self.cam = rig["left"]
        self.fx, self.fy, self.cx, self.cy = rig["fx"], rig["fy"], rig["cx"], rig["cy"]
        self.baseline = float(rig["baseline"])
        self.near, self.far = [float(x) for x in zed_cfg.get("depth_range", [0.1, 15.0])]
        self.sim_time = sim_time
        self.ns = ns.strip("/")
        f = features
        self.cloud_on = f.on("depth.publish_point_cloud")
        self.cloud_interval = 1.0 / max(float(f.get("depth.point_cloud_freq", 10.0) or 30.0), 0.5)
        self.stride = _RES_STRIDE.get(str(f.get("depth.point_cloud_res", "COMPACT")).upper(), 4)
        self.disp_on = f.on("depth.publish_disparity")
        self.map_on = f.on("mapping.mapping_enabled")
        self.map_res = min(max(float(f.get("mapping.resolution", 0.05)), 0.01), 0.2)
        self.map_range = float(f.get("mapping.max_mapping_range", 5.0))
        self.map_range = self.far if self.map_range <= 0 else self.map_range
        self.map_pub_interval = 1.0 / max(float(f.get("mapping.fused_pointcloud_freq", 1.0) or 1.0), 0.1)
        self.map_integrate_interval = 0.25  # fuse a depth frame every 0.25 s (wall)

        view = zed_cfg.get("view", {}) or {}
        # GUI overlay: a map that ACCUMULATES the depth frames (placed with the camera pose, voxel-deduplicated), plus a
        # translucent grid showing the camera's field of view. The old single-frame live cloud is opt-in (point_cloud).
        self.draw_cloud = bool(has_ui and view.get("point_cloud", False))
        self.draw_map = bool(has_ui and view.get("accumulate", view.get("fused_cloud", True)))
        self.draw_fov = bool(has_ui and view.get("fov_grid", True))
        self.fov_range = min(float(view.get("fov_range", 3.0)), self.far)
        self.fov_color = [float(x) for x in view.get("fov_color", [0.2, 0.8, 1.0, 0.55])]
        self.map_draw_interval = 1.0 / max(float(view.get("map_draw_hz", 1.0)), 0.1)
        self.map_integrate = self.map_on or self.draw_map     # integrate frames for the ROS map and/or the GUI map
        self.draw_stride = max(1, int(view.get("draw_stride", 8)))
        self.draw_interval = 1.0 / max(float(view.get("draw_hz", 5.0)), 0.5)
        self.draw_color = str(view.get("draw_color", "depth"))
        self.point_size = float(view.get("point_size", 4.0))
        self.map_point_size = float(view.get("map_point_size", 3.0))
        self.map_draw_max = int(view.get("map_draw_max_points", 80000))

        self.lut = _turbo_lut()[::-1]
        self.t = {"cloud": 0.0, "disp": 0.0, "draw": 0.0, "map_in": 0.0, "map_pub": 0.0, "map_draw": 0.0}
        self.enabled = True
        self._rays = {}
        self._poses = collections.deque(maxlen=400)  # (sim time, R, pos) of the left camera, ~1.6 s at 250 Hz
        self.map_keys = np.zeros(0, np.int64)
        self.map_xyz = np.zeros((0, 3), np.float32)
        self.map_rgb = np.zeros(0, np.uint32)
        self._last_cloud_render_time = None
        self._map_draw_dirty = False

        from isaacsim.core.experimental.utils.app import enable_extension  # noqa: WPS433
        enable_extension("isaacsim.ros2.bridge")
        import rclpy  # noqa: WPS433
        from rclpy.qos import qos_profile_sensor_data  # noqa: WPS433
        from sensor_msgs.msg import PointCloud2, PointField  # noqa: WPS433
        from stereo_msgs.msg import DisparityImage  # noqa: WPS433
        try:
            rclpy.init()
        except RuntimeError:  # already initialised (SimClock / Pegasus)
            pass
        self.PointCloud2, self.DisparityImage = PointCloud2, DisparityImage
        self.fields = [PointField(name=n, offset=4 * i, datatype=PointField.FLOAT32, count=1)
                       for i, n in enumerate(("x", "y", "z", "rgb"))]
        self.node = rclpy.create_node("zed_depth_products", namespace=ns)
        q = qos_profile_sensor_data
        self.pub_cloud = self.node.create_publisher(PointCloud2, "zed/zed_node/point_cloud/cloud_registered", q) \
            if self.cloud_on else None
        self.pub_disp = self.node.create_publisher(DisparityImage, "zed/zed_node/disparity/disparity_image", q) \
            if self.disp_on else None
        self.pub_map = self.node.create_publisher(PointCloud2, "zed/zed_node/mapping/fused_cloud", q) \
            if self.map_on else None

        if self.draw_cloud or self.draw_map or self.draw_fov:
            # Draw through the viewport's own scene layer (RegisterScene), which Kit stacks *under* the HUD
            # and menu bar; a frame of our own would sit on top and cover the HUD text.
            import omni.ui.scene as sc  # noqa: WPS433
            from omni.kit.viewport.registry import RegisterScene  # noqa: WPS433
            owner = self
            empty = dict(colors=[[0.0, 0.0, 0.0, 0.0]], sizes=[0.0])

            class _CloudScene:
                name = "bisg ZED cloud"
                categories = ("bisg",)
                visible = True

                def __init__(self, desc):
                    owner.sc_map = sc.Points([[0.0, 0.0, 0.0]], **empty)
                    owner.sc_cloud = sc.Points([[0.0, 0.0, 0.0]], **empty)
                    owner.sc_fov = None
                    if owner.draw_fov:
                        owner.sc_fov = sc.Transform()       # moved with the camera pose in maybe_update
                        with owner.sc_fov:
                            owner._build_fov(sc)

            self._scene_reg = RegisterScene(_CloudScene, f"bisg.zed_depth.{ns}")
            if not hasattr(self, "sc_cloud"):
                LOG.warning("zed depth: no viewport scene layer, not drawing")
                self.draw_cloud = self.draw_map = self.draw_fov = False
        LOG.info("zed depth: point_cloud %s (%.0f Hz, %s), disparity %s, mapping %s%s; GUI live cloud %s, accumulated map %s, fov grid %s",
                 "on" if self.cloud_on else "off", 1.0 / self.cloud_interval,
                 f"every {self.stride}th px", "on" if self.disp_on else "off",
                 "on" if self.map_on else "off",
                 f" ({self.map_res * 100:.0f} cm voxels, <= {self.map_range:.1f} m, {1.0 / self.map_pub_interval:.1f} Hz)"
                 if self.map_on else "", "on" if self.draw_cloud else "off", "on" if self.draw_map else "off",
                 f"on ({self.fov_range:g} m)" if self.draw_fov else "off")

    # ---------------------------------------------------------------------------------------------
    def _due(self, key, interval, now):
        if now - self.t[key] >= interval:
            self.t[key] = now
            return True
        return False

    def maybe_update(self):
        """Run whatever is due. Never raises."""
        if not self.enabled:
            return
        now = time.time()
        if self.map_integrate or self.draw_cloud or self.draw_fov:
            try:  # every call (= every physics step): pose history for render-time lookup
                pos, q = self.cam.get_world_pose(camera_axes="world")  # world axes = FLU
                R, t = _quat_wxyz_to_matrix(q), np.asarray(pos, np.float64)
                self._poses.append((self.sim_time(), R, t))
                if self.draw_fov and getattr(self, "sc_fov", None) is not None:
                    # omni.ui.scene is row-vector: p' = p @ M with M = [[R^T, 0], [t, 1]]
                    m = np.eye(4)
                    m[:3, :3], m[3, :3] = R.T, t
                    self.sc_fov.transform = m.flatten().tolist()
            except Exception:  # noqa: BLE001
                pass
        jobs = {
            "cloud": self.cloud_on and self.pub_cloud.get_subscription_count() > 0 and self._due("cloud", self.cloud_interval, now),
            "disp": self.disp_on and self.pub_disp.get_subscription_count() > 0 and self._due("disp", self.cloud_interval, now),
            "map_in": self.map_integrate and self._due("map_in", self.map_integrate_interval, now),
            "draw": (self.draw_cloud and self._due("draw", self.draw_interval, now))
                    or (self.draw_map and self._map_draw_dirty and self._due("map_draw", self.map_draw_interval, now)),
        }
        map_pub = self.map_on and self.pub_map.get_subscription_count() > 0 and self._due("map_pub", self.map_pub_interval, now)
        if not (any(jobs.values()) or map_pub):
            return
        try:
            # One rendered frame: depth, colour and render time belong together.
            frame = self.cam.get_current_frame()
            depth, rgba, t_render = frame.get("distance_to_image_plane"), frame.get("rgb"), frame.get("rendering_time")
            if depth is None or np.size(depth) == 0 or not t_render:
                return
            rgba = None if rgba is None or np.size(rgba) == 0 else np.asarray(rgba, np.uint8)
            depth = np.asarray(depth, np.float32)
            h, w = depth.shape[:2]
            depth = depth.reshape(h, w)
            stamp = self._stamp(float(t_render))
            pose = None
            if jobs["map_in"] or jobs["draw"]:
                pose = self._pose_at(float(t_render))
                if pose is None:  # history doesn't reach back that far yet
                    jobs["map_in"] = jobs["draw"] = False
            if jobs["cloud"]:
                self._publish_cloud(depth, rgba, stamp)
            if jobs["disp"]:
                self._publish_disparity(depth, stamp)
            if jobs["map_in"]:
                self._integrate_map(depth, rgba, pose)
            if map_pub:
                self._publish_map(stamp)
            if jobs["draw"]:
                self._draw(depth, rgba, pose, float(t_render))
        except Exception as exc:  # noqa: BLE001 — never stop the sim for a sensor product
            LOG.warning("zed depth: update failed, disabling (%s)", exc)
            self.enabled = False

    # ---------------------------------------------------------------------------------------------
    def _stamp(self, t):
        from builtin_interfaces.msg import Time  # noqa: WPS433
        sec, nsec = divmod(int(round(t * 1e9)), 1_000_000_000)
        return Time(sec=sec, nanosec=nsec)

    def _pose_at(self, t):
        """Camera pose (R, pos) recorded closest to sim time t, or None if t is outside the history."""
        if not self._poses or t < self._poses[0][0] - 0.01:
            return None
        times = [p[0] for p in self._poses]
        i = bisect.bisect_left(times, t)
        cand = [j for j in (i - 1, i) if 0 <= j < len(times)]
        j = min(cand, key=lambda k: abs(times[k] - t))
        return None if abs(times[j] - t) > 0.02 else self._poses[j][1:]

    def _points(self, depth, stride, max_range=None):
        """Camera-frame (FLU) points for every `stride`-th pixel: (rows, cols, 3), NaN where no depth."""
        h, w = depth.shape
        if stride not in self._rays:
            v, u = np.mgrid[0:h:stride, 0:w:stride].astype(np.float32)
            self._rays[stride] = np.stack([np.ones_like(u), -(u - self.cx) / self.fx, -(v - self.cy) / self.fy], -1)
        d = depth[::stride, ::stride]
        hi = self.far if max_range is None else min(self.far, max_range)
        d = np.where(np.isfinite(d) & (d >= self.near) & (d <= hi), d, np.nan).astype(np.float32)
        return self._rays[stride] * d[..., None], d

    def _cloud_msg(self, xyz, rgb, frame, stamp, rows, cols, dense):
        cloud = np.empty((xyz.shape[0], 4), np.float32)
        cloud[:, :3] = xyz
        cloud[:, 3] = rgb.view(np.float32)  # PCL packs 0x00RRGGBB into the float's bits
        m = self.PointCloud2()
        m.header.stamp, m.header.frame_id = stamp, frame
        m.height, m.width = rows, cols
        m.fields, m.is_bigendian, m.point_step, m.row_step, m.is_dense = self.fields, False, 16, 16 * cols, dense
        m.data = cloud.tobytes()
        return m

    def _publish_cloud(self, depth, rgba, stamp):
        pts, _ = self._points(depth, self.stride)
        rows, cols = pts.shape[:2]
        rgb = _pack_rgb(rgba[::self.stride, ::self.stride, :3]).reshape(-1) if rgba is not None \
            else np.zeros(rows * cols, np.uint32)
        self.pub_cloud.publish(self._cloud_msg(pts.reshape(-1, 3), rgb, f"{self.ns}/zed_left_camera_frame",
                                               stamp, rows, cols, dense=False))

    def _publish_disparity(self, depth, stamp):
        fb = self.fx * self.baseline
        valid = np.isfinite(depth) & (depth > 0)
        disp = np.where(valid, fb / np.where(valid, depth, 1.0), 0.0).astype(np.float32)  # 0 = invalid
        m = self.DisparityImage()
        m.header.stamp, m.header.frame_id = stamp, f"{self.ns}/zed_left_camera_optical_frame"
        img = m.image
        img.header = m.header
        img.height, img.width = disp.shape
        img.encoding, img.is_bigendian, img.step = "32FC1", 0, disp.shape[1] * 4
        img.data = disp.tobytes()
        m.f, m.t = float(self.fx), float(self.baseline)
        m.min_disparity, m.max_disparity = float(fb / self.far), float(fb / self.near)
        m.delta_d = 0.0  # exact (sim depth has no quantisation)
        m.valid_window.width, m.valid_window.height = disp.shape[1], disp.shape[0]
        self.pub_disp.publish(m)

    def _integrate_map(self, depth, rgba, pose):
        pts, d = self._points(depth, 4, self.map_range)
        ok = np.isfinite(d)
        if not ok.any():
            return
        R, t = pose
        world = pts[ok] @ R.T + t
        idx = np.floor(world / self.map_res).astype(np.int64) + _OFF
        keys = (idx[:, 0] << 42) | (idx[:, 1] << 21) | idx[:, 2]
        rgb = _pack_rgb(rgba[::4, ::4, :3][ok]) if rgba is not None else np.zeros(len(keys), np.uint32)
        keys, first = np.unique(keys, return_index=True)
        new = ~np.isin(keys, self.map_keys, assume_unique=True)
        if not new.any():
            return
        centres = ((idx[first[new]] - _OFF) + 0.5) * self.map_res
        self.map_keys = np.concatenate([self.map_keys, keys[new]])
        self.map_xyz = np.concatenate([self.map_xyz, centres.astype(np.float32)])
        self.map_rgb = np.concatenate([self.map_rgb, rgb[first[new]]])
        self._map_draw_dirty = True

    def _build_fov(self, sc):
        """Camera-frame (FLU, x forward) frustum: edges, the far rectangle and cross lines, plus nearer rectangles."""
        d = self.fov_range
        hy, hz = self.cx / self.fx, self.cy / self.fy       # tan(half FOV) across / down the image
        col = self.fov_color
        faint = [col[0], col[1], col[2], col[3] * 0.45]

        def rect(x, color, th):
            c = [(x, x * hy, x * hz), (x, -x * hy, x * hz), (x, -x * hy, -x * hz), (x, x * hy, -x * hz)]
            for a, b in zip(c, c[1:] + c[:1]):
                sc.Line(list(a), list(b), color=color, thickness=th)

        for sy in (1, -1):
            for sz in (1, -1):
                sc.Line([0.0, 0.0, 0.0], [d, sy * d * hy, sz * d * hz], color=col, thickness=3)
        for k in (1, 2, 3):
            rect(d * k / 3.0, col if k == 3 else faint, 3 if k == 3 else 2)
        n = 6                                              # grid on the far plane
        for i in range(1, n):
            f = -1.0 + 2.0 * i / n
            sc.Line([d, f * d * hy, d * hz], [d, f * d * hy, -d * hz], color=faint, thickness=2)
            sc.Line([d, d * hy, f * d * hz], [d, -d * hy, f * d * hz], color=faint, thickness=2)
        # translucent far plane, so the FOV reads as a surface rather than loose lines (axis 1 = plane normal along x)
        with sc.Transform(transform=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, d, 0, 0, 1]):
            sc.Rectangle(2 * d * hy, 2 * d * hz, color=[col[0], col[1], col[2], 0.12], axis=1)

    def _publish_map(self, stamp):
        n = len(self.map_keys)
        if n:
            self.pub_map.publish(self._cloud_msg(self.map_xyz, self.map_rgb, f"{self.ns}/odom", stamp, 1, n, dense=True))

    def _draw(self, depth, rgba, pose, render_time):
        # Keep the UI scene primitives alive. Replace live-cloud buffers only for a
        # genuinely new camera render; fused-map buffers change only when integration
        # adds previously unseen voxels.
        if self.draw_cloud and render_time != self._last_cloud_render_time:
            pts, d = self._points(depth, self.draw_stride)
            ok = np.isfinite(d)
            if ok.any():
                R, t = pose
                world = pts[ok] @ R.T + t
                if self.draw_color == "rgb" and rgba is not None:
                    col = rgba[::self.draw_stride, ::self.draw_stride, :3][ok] / 255.0
                else:
                    norm = (np.log(np.clip(d[ok], self.near, self.far)) - np.log(self.near)) / (np.log(self.far) - np.log(self.near))
                    col = self.lut[(np.clip(norm, 0, 1) * 255).astype(np.uint8)] / 255.0
                self.sc_cloud.positions = world.tolist()
                self.sc_cloud.colors = np.concatenate([col, np.ones((len(col), 1))], 1).tolist()
                self.sc_cloud.sizes = [self.point_size] * len(world)
            else:
                # Clear a previously visible cloud when a new frame has no valid depth.
                self.sc_cloud.positions = [[0.0, 0.0, 0.0]]
                self.sc_cloud.colors = [[0.0, 0.0, 0.0, 0.0]]
                self.sc_cloud.sizes = [0.0]
            self._last_cloud_render_time = render_time
        if self.draw_map and self._map_draw_dirty:
            self._map_draw_dirty = False
            if not len(self.map_keys):
                return
            sel = np.arange(len(self.map_keys))
            if len(sel) > self.map_draw_max:
                sel = sel[:: int(np.ceil(len(sel) / self.map_draw_max))]
            c = self.map_rgb[sel]
            col = np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], 1) / 255.0
            self.sc_map.positions = self.map_xyz[sel].tolist()
            self.sc_map.colors = np.concatenate([col, np.ones((len(col), 1))], 1).tolist()
            self.sc_map.sizes = [self.map_point_size] * len(sel)
