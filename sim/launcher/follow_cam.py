"""
Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode: the free perspective camera keeps looking at
the drone and moves with it, and you can still orbit / zoom around it with the mouse (the camera keeps whatever offset you
leave it at). Not a new camera: it re-aims Kit's own /OmniverseKit_Persp every rendered frame with
ViewportManager.set_camera_view(eye, target), which also keeps the Kit orbit pivot (centre of interest) on the drone.

  smooth_s    low-pass time constant (s) on the followed position: 0 = rigid, ~0.3 = soft, ~1 = lazy
  follow_yaw  true = chase view: the camera swings round with the drone's heading
  offset      where "Reset view" puts the camera, drone body frame FLU (x forward, y left, z up), metres
  look_height metres above the drone's centre the camera aims at

A small "Follow camera" window changes all of that live. Only acts while the viewport shows /OmniverseKit_Persp
(pick another camera in the viewport menu and it stands down).
"""
import logging
import math
import time

import numpy as np
from scipy.spatial.transform import Rotation

LOG = logging.getLogger("launch")
PERSP = "/OmniverseKit_Persp"


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class FollowCam:
    def __init__(self, vehicles, cfg: dict):
        import omni.ui as ui  # noqa: WPS433
        from omni.kit.viewport.utility import get_active_viewport  # noqa: WPS433

        self.vehicles = vehicles
        self.idx = max(0, min(int(cfg.get("drone", 1)) - 1, len(vehicles) - 1))
        self.offset = np.array([float(x) for x in cfg.get("offset", [-3.0, 0.0, 1.5])])
        self.look_h = float(cfg.get("look_height", 0.0))
        self._get_vp = get_active_viewport

        self.m_on = ui.SimpleBoolModel(bool(cfg.get("enabled", True)))
        self.m_yaw = ui.SimpleBoolModel(bool(cfg.get("follow_yaw", False)))
        self.m_smooth = ui.SimpleFloatModel(float(cfg.get("smooth_s", 0.3)))
        self.m_drone = ui.SimpleIntModel(self.idx + 1)
        self.m_on.add_value_changed_fn(lambda m: self._restart())
        self.m_drone.add_value_changed_fn(lambda m: self._set_drone(m.as_int))
        self.m_dist = ui.SimpleFloatModel(float(-self.offset[0]))    # metres behind the drone
        self.m_height = ui.SimpleFloatModel(float(self.offset[2]))   # metres above it
        self.m_dist.add_value_changed_fn(lambda m: self._offset_changed())
        self.m_height.add_value_changed_fn(lambda m: self._offset_changed())

        self.window = ui.Window("Follow camera", width=290, height=270, visible=bool(cfg.get("window", True)))
        with self.window.frame:
            with ui.VStack(spacing=6, height=0):
                with ui.HStack(height=22):
                    ui.CheckBox(self.m_on, width=24)
                    ui.Label("Follow the drone")
                with ui.HStack(height=22):
                    ui.CheckBox(self.m_yaw, width=24)
                    ui.Label("Turn with its heading (chase)")
                with ui.HStack(height=22):
                    ui.Label("Smoothing (s)", width=100)
                    ui.FloatSlider(self.m_smooth, min=0.0, max=2.0)
                if len(vehicles) > 1:
                    with ui.HStack(height=22):
                        ui.Label("Drone #", width=100)
                        ui.IntSlider(self.m_drone, min=1, max=len(vehicles))
                with ui.HStack(height=22):
                    ui.Label("Distance (m)", width=100)
                    ui.FloatSlider(self.m_dist, min=0.5, max=15.0)
                with ui.HStack(height=22):
                    ui.Label("Height (m)", width=100)
                    ui.FloatSlider(self.m_height, min=-1.0, max=10.0)
                ui.Button("Reset view behind the drone", height=26, clicked_fn=self.reset_view)
                ui.Label("Mouse orbit / zoom still works; the camera keeps your offset.", word_wrap=True, height=30,
                         style={"font_size": 12})
        self.window.deferred_dock_in("Content", ui.DockPolicy.DO_NOTHING)  # stays floating; drag it where you like
        self.window.position_x, self.window.position_y = 140, 150

        self._ps = None            # smoothed followed position
        self._yaw = 0.0            # smoothed heading
        self._prev_target = None
        self._t = time.monotonic()
        self._ready = True
        self.reset_view()
        LOG.info("follow cam: drone %d, offset %s, smooth %.2fs, yaw-follow %s", self.idx + 1,
                 self.offset.tolist(), self.m_smooth.as_float, self.m_yaw.as_bool)

    # -- state ------------------------------------------------------------------------------------------------
    def _pose(self):
        st = self.vehicles[self.idx].state
        yaw = Rotation.from_quat(st.attitude).as_euler("ZYX")[0]
        return np.array(st.position, dtype=float), float(yaw)

    def _set_drone(self, n):
        self.idx = max(0, min(int(n) - 1, len(self.vehicles) - 1))
        self.reset_view()

    def _offset_changed(self):
        if not getattr(self, "_ready", False):
            return
        self.offset = np.array([-self.m_dist.as_float, self.offset[1], self.m_height.as_float])
        self.reset_view()

    def _restart(self):
        self._ps = None
        self._prev_target = None

    def _camera_ok(self):
        vp = self._get_vp()
        return vp is not None and str(vp.camera_path) == PERSP

    def _set_view(self, eye, target):
        from isaacsim.core.rendering_manager import ViewportManager  # noqa: WPS433
        ViewportManager.set_camera_view(PERSP, eye=[float(x) for x in eye], target=[float(x) for x in target])

    def reset_view(self):
        """Put the camera at `offset` in the drone's body frame, looking at it."""
        p, yaw = self._pose()
        self._ps, self._yaw = p.copy(), yaw
        rz = Rotation.from_euler("z", yaw).as_matrix()
        target = p + np.array([0.0, 0.0, self.look_h])
        if self._camera_ok():
            self._set_view(p + rz @ self.offset, target)
        self._prev_target = target

    # -- every rendered frame ---------------------------------------------------------------------------------
    def update(self):
        if not self.m_on.as_bool or not self._camera_ok():
            self._prev_target = None
            return
        try:
            now = time.monotonic()
            dt, self._t = now - self._t, now
            p, yaw = self._pose()
            fresh = self._ps is None                       # just (re-)enabled: keep the camera where it is
            if fresh:
                self._ps, self._yaw = p.copy(), yaw
            tau = max(self.m_smooth.as_float, 0.0)
            a = 1.0 if tau < 1e-3 else 1.0 - math.exp(-dt / tau)
            self._ps = self._ps + (p - self._ps) * a
            dyaw = _wrap(yaw - self._yaw) * a
            self._yaw = _wrap(self._yaw + dyaw)
            target = self._ps + np.array([0.0, 0.0, self.look_h])

            from pxr import Gf, Usd, UsdGeom  # noqa: WPS433
            import omni.usd  # noqa: WPS433
            prim = omni.usd.get_context().get_stage().GetPrimAtPath(PERSP)
            eye = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation())
            if self._prev_target is None:
                self._prev_target = target
            rel = eye - self._prev_target                    # the offset you (or the last frame) left the camera at
            if self.m_yaw.as_bool and dyaw:
                rel = Rotation.from_euler("z", dyaw).as_matrix() @ rel
            self._set_view(target + rel, target)
            self._prev_target = target
        except Exception as exc:  # noqa: BLE001 — a camera helper must never stop the sim
            LOG.warning("follow cam: disabled (%s)", exc)
            self.m_on.set_value(False)
