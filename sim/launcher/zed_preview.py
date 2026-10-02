"""
Live ZED view in the Isaac GUI: left camera image and its depth, side by side, as a second
camera perspective next to the main viewport.

Reads the rig's own render products (Camera.get_rgba / get_depth, the same data the ROS writers
publish), so it works at HD720 even when DDS can't carry the frames (docs/bugs.md B2).
Enabled by `sensors.zed.preview` in the scenario; ignored when there is no UI (plain headless).

Depth colouring follows ZED Explorer: red = near, blue = far, log scale over the rig's
depth_range; black = no depth (+inf beyond range, NaN).
"""
import logging
import time

import numpy as np

LOG = logging.getLogger("launch")


def _turbo_lut():
    """Google Turbo colormap, 256 entries, as uint8 RGB (polynomial approximation)."""
    x = np.linspace(0.0, 1.0, 256)[:, None]
    c = np.array([[0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943],
                  [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604],
                  [0.10667330, 12.64194608, -60.58204836, 110.36276771, -89.90310912, 27.34824973]])
    rgb = np.concatenate([x ** i for i in range(6)], axis=1) @ c.T
    return (np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8)


class ZedPreview:
    def __init__(self, cams: dict, ns: str, cfg: dict):
        import omni.ui as ui  # noqa: WPS433 — only importable once Kit's UI is up

        self.cam = cams["left"]
        self.near, self.far = [float(x) for x in cfg.get("depth_range", [0.1, 15.0])]
        self.interval = 1.0 / max(float(cfg.get("preview_hz", 5.0)), 0.5)
        self.t_last = 0.0
        self.enabled = True
        # Near = red: index 255 of Turbo is dark red, 0 is dark blue.
        self.lut = _turbo_lut()[::-1]
        self._log_near, self._log_span = np.log(self.near), np.log(self.far) - np.log(self.near)

        self.p_rgb = ui.ByteImageProvider()
        self.p_depth = ui.ByteImageProvider()
        self.window = ui.Window(f"ZED Mini {ns} - left | depth", width=960, height=330)
        fit = ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT
        with self.window.frame:
            with ui.VStack(spacing=4):
                with ui.HStack(spacing=4):
                    ui.ImageWithProvider(self.p_rgb, fill_policy=fit)
                    ui.ImageWithProvider(self.p_depth, fill_policy=fit)
                self.label = ui.Label("waiting for the first ZED frame...", height=18)
        # Tab next to the Content browser (bottom panel) so it doesn't cover the viewport; drag it out to float.
        self.window.deferred_dock_in("Content", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        LOG.info("zed preview: window '%s' (%.0f Hz, depth %.2f-%.1f m, red = near)",
                 self.window.title, 1.0 / self.interval, self.near, self.far)

    def maybe_update(self):
        """Refresh the window if the interval has elapsed. Never raises."""
        if not self.enabled:
            return
        now = time.time()
        if now - self.t_last < self.interval:
            return
        self.t_last = now
        try:
            rgba = self.cam.get_rgba()
            depth = self.cam.get_depth()
            if rgba is None or depth is None or rgba.size == 0 or depth.size == 0:
                return
            rgba = np.ascontiguousarray(rgba, dtype=np.uint8)
            h, w = rgba.shape[:2]
            self.p_rgb.set_data_array(rgba, [w, h])

            d = np.asarray(depth, dtype=np.float32).reshape(h, w)
            valid = np.isfinite(d) & (d > 0)
            norm = (np.log(np.clip(np.where(valid, d, self.far), self.near, self.far)) - self._log_near) / self._log_span
            idx = (np.clip(norm, 0.0, 1.0) * 255).astype(np.uint8)
            vis = np.empty((h, w, 4), np.uint8)
            vis[..., :3] = self.lut[idx]
            vis[..., 3] = 255
            vis[~valid, :3] = 0
            self.p_depth.set_data_array(vis, [w, h])

            v = d[valid]
            if v.size:
                self.label.text = (f"{w}x{h}   depth min {v.min():.2f} m   median {np.median(v):.2f} m   "
                                   f"< 0.5 m {(v < 0.5).mean() * 100:.1f}%   no depth {(~valid).mean() * 100:.1f}%   "
                                   f"(red {self.near:g} m -> blue {self.far:g} m, log)")
        except Exception as exc:  # noqa: BLE001 — a broken preview must never stop the sim
            LOG.warning("zed preview: update failed, disabling (%s)", exc)
            self.enabled = False
