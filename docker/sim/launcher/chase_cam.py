"""
Chase camera of a vehicle as a ROS 2 image (scenario `sensors.chase_cam`, docs/interface-contract.md `chase/image`).

A third-person view for humans (QGC mosaic, RViz): its own USD camera sits `offset` behind/above the drone in the drone's yaw
frame and looks at it, so it turns with the heading. Unlike the GUI follow camera (follow_cam.py) it has its own render
product, so it also works headless and while the viewport shows something else. The pose is low-passed with `smooth_s`
(sim time: one step per rendered frame) and written to the camera prim every frame by `update()`.

  enabled      on/off
  resolution   [w, h] of the published image (640x360 = one tile of the 1280-wide QGC mosaic, no resize)
  hfov_deg     horizontal field of view
  offset       camera position in the drone's yaw frame FLU, m (x forward, y left, z up)
  look_height  aim this far above the drone's centre, m
  smooth_s     low-pass time constant on the followed position/heading, s (0 = rigid)

Published by the OmniGraph chain OnPlaybackTick -> IsaacCreateRenderProduct -> ROS2CameraHelper (rgb) on
/drone_<n>/chase/image. View only: no camera_info, no TF.
"""
import logging
import math

import numpy as np
import omni.graph.core as og
import omni.usd
import usdrt.Sdf
from isaacsim.core.experimental.utils.app import enable_extension
from pxr import Gf, UsdGeom
from scipy.spatial.transform import Rotation

LOG = logging.getLogger("launch")
H_APERTURE_MM = 20.955              # USD default; the focal length below sets the field of view


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class ChaseCam:
    def __init__(self, vehicle, vid: int, cfg: dict, dt: float):
        """`dt`: sim seconds between two update() calls (the rendering step), for the smoothing."""
        enable_extension("isaacsim.ros2.bridge")
        self.vehicle, self.dt = vehicle, float(dt)
        self.offset = np.array([float(x) for x in cfg.get("offset", [-2.0, 0.0, 1.0])])
        self.look_h = float(cfg.get("look_height", 0.0))
        self.tau = max(0.0, float(cfg.get("smooth_s", 0.3)))
        width, height = [int(x) for x in cfg.get("resolution", [640, 360])]
        hfov = math.radians(float(cfg.get("hfov_deg", 90.0)))

        self.path = f"/World/drone_{vid + 1}_chase_cam"
        cam = UsdGeom.Camera.Define(omni.usd.get_context().get_stage(), self.path)
        cam.CreateFocalLengthAttr(H_APERTURE_MM / (2.0 * math.tan(hfov / 2.0)))
        cam.CreateHorizontalApertureAttr(H_APERTURE_MM)
        cam.CreateVerticalApertureAttr(H_APERTURE_MM * height / width)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, 1000.0))
        xf = UsdGeom.Xformable(cam)
        self._t_op = xf.AddTranslateOp()
        self._r_op = xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble)
        self._ps, self._yaw = None, 0.0
        self.update()

        keys = og.Controller.Keys
        ns = f"/drone_{vid + 1}"
        og.Controller.edit(
            {"graph_path": f"/World/drone_{vid + 1}_chase_pub", "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: [("tick", "omni.graph.action.OnPlaybackTick"),
                                    ("rp", "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                                    ("pub", "isaacsim.ros2.bridge.ROS2CameraHelper")],
                keys.CONNECT: [("tick.outputs:tick", "rp.inputs:execIn"),
                               ("rp.outputs:execOut", "pub.inputs:execIn"),
                               ("rp.outputs:renderProductPath", "pub.inputs:renderProductPath")],
                keys.SET_VALUES: [("rp.inputs:cameraPrim", [usdrt.Sdf.Path(self.path)]),
                                  ("rp.inputs:width", width), ("rp.inputs:height", height),
                                  ("pub.inputs:topicName", "chase/image"), ("pub.inputs:nodeNamespace", ns),
                                  ("pub.inputs:frameId", f"drone_{vid + 1}/chase_cam"), ("pub.inputs:type", "rgb"),
                                  ("pub.inputs:resetSimulationTimeOnStop", True)],
            },
        )
        LOG.info("chase cam: %dx%d %.0f deg at %s behind/above drone %d -> %s/chase/image",
                 width, height, math.degrees(hfov), self.offset.tolist(), vid + 1, ns)

    def update(self):
        """Move the camera to this frame's chase pose (call once per rendered frame)."""
        st = self.vehicle.state
        p = np.asarray(st.position, dtype=float)
        yaw = float(Rotation.from_quat(st.attitude).as_euler("ZYX")[0])
        if self._ps is None:
            self._ps, self._yaw = p.copy(), yaw
        a = 1.0 if self.tau < 1e-3 else 1.0 - math.exp(-self.dt / self.tau)
        self._ps = self._ps + (p - self._ps) * a
        self._yaw = _wrap(self._yaw + _wrap(yaw - self._yaw) * a)
        target = self._ps + np.array([0.0, 0.0, self.look_h])
        eye = self._ps + Rotation.from_euler("z", self._yaw).as_matrix() @ self.offset
        fwd = target - eye
        fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        x, y, z, w = Rotation.from_matrix(np.stack([right, up, -fwd], axis=1)).as_quat()   # USD camera looks down -Z, +Y up
        self._t_op.Set(Gf.Vec3d(*[float(v) for v in eye]))
        self._r_op.Set(Gf.Quatd(float(w), Gf.Vec3d(float(x), float(y), float(z))))
