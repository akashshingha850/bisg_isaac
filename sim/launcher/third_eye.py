"""External trailing camera for a vehicle (no ROS topics)."""
import logging

import numpy as np
from scipy.spatial.transform import Rotation

LOG = logging.getLogger("launch")


def _quat_wxyz(rot: Rotation):
    x, y, z, w = rot.as_quat()
    return np.array([w, x, y, z])


def attach_third_eye(vehicle, cfg: dict):
    """Attach a camera behind and above the drone. Local coordinates use FLU axes."""
    from isaacsim.sensors.camera.camera import Camera

    width, height = [int(x) for x in cfg.get("resolution", [640, 360])]
    fps = float(cfg.get("fps", 15.0))
    pos = np.array([float(x) for x in cfg.get("position", [-5.0, 0.0, 2.0])])
    pitch = float(cfg.get("pitch_deg", 22.0))
    camera = Camera(prim_path=f"{vehicle.prim_path}/body/third_eye_camera",
                    frequency=fps, resolution=(width, height))
    camera.set_local_pose(pos, _quat_wxyz(Rotation.from_euler("Y", pitch, degrees=True)),
                          camera_axes="world")
    camera.initialize()
    camera.set_clipping_range(0.1, float(cfg.get("far", 100.0)))
    LOG.info("third-eye camera attached at body-local %s, %dx%d", pos.tolist(), width, height)
    return camera
