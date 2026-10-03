"""
ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.source: sdk`, docs/zed-sdk-sim.md).

Instead of publishing ROS topics itself (zed_rig.py, the emulated rig), the sim mounts Stereolabs' ZED_M
asset on the vehicle and streams stereo + IMU through the `sl.sensor.camera` extension (OmniGraph node
`ZED_Camera`). The unmodified zed_wrapper (`./bisg zed up`, compose service `zed`, the same image and
params as on the Jetson) connects with `sim_mode:=true` and publishes the contract's `zed/zed_node/*`
topics, TF, depth, point cloud and odometry from the SDK. Downstream code cannot tell sim from hardware.

Mounting follows Stereolabs' own robot examples (isaaclab_utils.author_zed_link_joint): the asset is a
top-level rigid body held by a FixedJoint to the vehicle body. A plain nested reference does NOT follow a
physics-driven parent (the camera stays at the spawn pose: black frames, odometry stuck at 0).

Needs the extension on Kit's ext path before SimulationApp starts: launch.py adds `--ext-folder` and
`--enable sl.sensor.camera` when any vehicle uses source `sdk` (see zed_source()).
"""
import logging

import numpy as np
import omni.graph.core as og
import omni.usd
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.utils.prims import set_targets
from pxr import Gf, PhysxSchema, Sdf, UsdGeom, UsdPhysics
from scipy.spatial.transform import Rotation

LOG = logging.getLogger("launch")

from zed_sdk_cfg import EXT_ID, stream_port  # noqa: E402 — stdlib-only half, also read before Kit starts


def _set_world_pose(prim, pos, rot: Rotation):
    """Author one translate + one orient op (wxyz) so the body starts exactly where the joint wants it."""
    xf = UsdGeom.Xformable(prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in pos]))
    x, y, z, w = rot.as_quat()
    xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(float(w), Gf.Vec3d(float(x), float(y), float(z))))


def attach_zed_sdk(vehicle, vehicle_id: int, ns: str, cfg: dict, spawn_pos, spawn_rot: Rotation):
    """Mount the ZED Mini twin on `vehicle` (Pegasus Multirotor) and start streaming it.

    cfg keys (`sensors.zed`, shared with the emulated rig where they overlap):
      mount_xyz_rpy: [x,y,z,roll_deg,pitch_deg,yaw_deg] of the camera on the vehicle body (FLU)
      resolution:    [w, h] -> SDK resolution token (HD720 = [1280, 720], also HD2K/HD1080/VGA)
      fps:           stream frame rate
      transport:     IPC (default; shared memory, wrapper container needs `ipc: host`) | NETWORK | BOTH
    Returns {"prim": str, "port": int}.
    """
    enable_extension(EXT_ID)
    from sl.sensor.camera.utils import get_camera_usd_path  # noqa: WPS433 — importable once the ext is enabled

    mount = [float(x) for x in cfg.get("mount_xyz_rpy", [0.18, 0.0, -0.02, 0, 0, 0])]
    mount_xyz, mount_rpy = np.array(mount[:3]), mount[3:]
    mount_rot = Rotation.from_euler("ZYX", [mount_rpy[2], mount_rpy[1], mount_rpy[0]], degrees=True)
    width, height = [int(x) for x in cfg.get("resolution", [1280, 720])]
    token = {(2208, 1242): "HD2K", (1920, 1080): "HD1080", (1280, 720): "HD720", (672, 376): "VGA"}.get((width, height))
    if token is None:
        raise SystemExit(f"[launch] ZED Mini resolution {width}x{height} is not a ZED_M mode "
                         f"(HD2K 2208x1242, HD1080 1920x1080, HD720 1280x720, VGA 672x376)")
    fps = int(cfg.get("fps", 30))
    transport = str(cfg.get("transport", "IPC")).upper()
    port = stream_port(vehicle_id)

    stage = omni.usd.get_context().get_stage()
    body_path = f"{vehicle.prim_path}/body"
    zed_path = f"/World/drone_{vehicle_id + 1}_zed"
    usd = get_camera_usd_path("ZED_M")
    if not usd:
        raise SystemExit("[launch] extension has no ZED_M asset (is it the v5.2.x line? docs/zed-sdk-sim.md)")

    prim = stage.DefinePrim(zed_path, "Xform")
    prim.GetReferences().AddReference(usd)
    # Start where the joint will hold it: spawn pose of the vehicle composed with the mount.
    _set_world_pose(prim, np.array(spawn_pos) + spawn_rot.apply(mount_xyz), spawn_rot * mount_rot)

    # The asset root carries its own rigid-body + mass. It is a sensor, not payload: make it weightless so it
    # neither loads the joint nor shifts the vehicle's hover thrust (PX4 params assume the Iris mass).
    UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(1e-3)
    PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(True)

    joint = UsdPhysics.FixedJoint.Define(stage, Sdf.Path(f"{zed_path}/fixjoint"))
    joint.CreateBody0Rel().SetTargets([Sdf.Path(body_path)])
    joint.CreateBody1Rel().SetTargets([Sdf.Path(zed_path)])
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*[float(v) for v in mount_xyz]))
    x, y, z, w = mount_rot.as_quat()
    joint.CreateLocalRot0Attr().Set(Gf.Quatf(float(w), float(x), float(y), float(z)))
    joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

    keys = og.Controller.Keys
    graph_path = f"/World/zed_stream_{vehicle_id + 1}"
    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [("tick", "omni.graph.action.OnPlaybackTick"), ("zed", "sl.sensor.camera.ZED_Camera")],
            keys.CONNECT: [("tick.outputs:tick", "zed.inputs:execIn")],
            keys.SET_VALUES: [
                ("zed.inputs:cameraModel", "ZED_M"),
                ("zed.inputs:resolution", token),
                ("zed.inputs:fps", fps),
                ("zed.inputs:streamingPort", port),
                ("zed.inputs:transportLayerMode", transport),
            ],
        },
    )
    set_targets(prim=stage.GetPrimAtPath(f"{graph_path}/zed"), attribute="inputs:cameraPrim", target_prim_paths=[zed_path])
    LOG.info("zed sdk rig: ZED_M %s %d fps at %s on %s, streaming %s on port %d (wrapper: ./bisg zed up)",
             token, fps, mount_xyz.tolist(), body_path, transport, port)
    return {"prim": zed_path, "port": port}
