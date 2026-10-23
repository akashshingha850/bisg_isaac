"""
ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.enabled`, docs/zed-sdk-sim.md).

The sim does not publish camera topics itself: it mounts Stereolabs' ZED_M
asset on the vehicle and streams stereo + IMU through the `sl.sensor.camera` extension (OmniGraph node
`ZED_Camera`). The unmodified zed_wrapper (`./bisg zed up`, compose service `zed`, the same image and
params as on the Jetson) connects with `sim_mode:=true` and publishes the contract's `zed/zed_node/*`
topics, TF, depth, point cloud and odometry from the SDK. Downstream code cannot tell sim from hardware.

Mounting follows Stereolabs' own robot examples (isaaclab_utils.author_zed_link_joint): the asset is a
top-level rigid body held by a FixedJoint to the vehicle body. A plain nested reference does NOT follow a
physics-driven parent (the camera stays at the spawn pose: black frames, odometry stuck at 0).

Needs the extension on Kit's ext path before SimulationApp starts: launch.py adds `--ext-folder` and
`--enable sl.sensor.camera` when any vehicle has `sensors.zed.enabled`.
"""
import logging

import numpy as np
import omni.graph.core as og
import omni.usd
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.utils import stage as _stage_utils
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


# The ZED_M asset (extension v5.2.1, unchanged in v5.3.0; ZED_2i the same) authors its Imu_Sensor at orient (w, x, y, z) =
# (0.5, 0.5, -0.5, -0.5), a 90 deg rotation, while the extension's stream conversion and the SDK expect it aligned with the
# camera body (x forward, z up): the wrapper's imu/data at rest read accel (0, +9.81, 0), rpy (90, 0, -90), which blocked IMU
# fusion. Body-aligned (identity), the wrapper reads accel (0, 0, +9.81), rpy (0, 0, 0) like the sim's physics IMU, and a
# rotated prim comes out as exactly its own attitude (measured 2026-10-22 at rpy (0, 90, 90) and (-90, 0, 0)).
STREAM_IMU_RPY = [0.0, 0.0, 0.0]     # [roll, pitch, yaw] deg of Imu_Sensor in the ZED_M asset, relative to its camera body


def _rotate_stream_imu(stage, imu_path, rpy):
    """Orient the streamed Imu_Sensor prim by `rpy` (sensors.zed.stream_imu_rpy), keeping its position."""
    prim = stage.GetPrimAtPath(imu_path)
    if not prim.IsValid():
        LOG.warning("zed sdk rig: no %s in the ZED_M asset; streamed IMU left as authored", imu_path)
        return
    rpy = [float(v) for v in rpy]
    x, y, z, w = Rotation.from_euler("ZYX", rpy[::-1], degrees=True).as_quat()
    xf = UsdGeom.Xformable(prim)
    ops = {op.GetOpType(): op for op in xf.GetOrderedXformOps()}
    orient = ops.get(UsdGeom.XformOp.TypeOrient)
    if orient is None:   # the asset authors translate + orient (quatf); add one if a future asset does not
        orient = xf.AddOrientOp(UsdGeom.XformOp.PrecisionFloat)
    if ops.keys() - {UsdGeom.XformOp.TypeTranslate, UsdGeom.XformOp.TypeOrient, UsdGeom.XformOp.TypeScale}:
        LOG.warning("zed sdk rig: %s has xform ops %s besides translate/orient/scale", imu_path, list(ops))
    quat = Gf.Quatf if orient.GetPrecision() == UsdGeom.XformOp.PrecisionFloat else Gf.Quatd
    vec = Gf.Vec3f if quat is Gf.Quatf else Gf.Vec3d
    orient.Set(quat(float(w), vec(float(x), float(y), float(z))))
    LOG.info("zed sdk rig: streamed IMU %s rotated rpy %s deg", imu_path, rpy)


def attach_zed_sdk(vehicle, vehicle_id: int, ns: str, cfg: dict, spawn_pos, spawn_rot: Rotation):
    """Mount the ZED Mini twin on `vehicle` (Pegasus Multirotor) and start streaming it.

    cfg keys (`sensors.zed`):
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

    _rotate_stream_imu(stage, f"{zed_path}/base_link/ZED_M/Imu_Sensor", cfg.get("stream_imu_rpy", STREAM_IMU_RPY))

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


def publish_imu(body_path: str, ns: str, imu_local, imu_rate: float = 200.0, publish: bool = True):
    """Physically-simulated IMU on `{body_path}/zed_imu_link`, published on `{ns}/zed/zed_node/imu/data`.

    The sim-side stand-in for the wrapper's own `imu/data` (the streamed ZED has no usable sensor channel,
    docs/zed-sdk-sim.md). Returns the IMUSensor.
    """
    enable_extension("isaacsim.ros2.bridge")
    enable_extension("isaacsim.sensors.experimental.physics")   # the old isaacsim.sensors.physics does not load
    from isaacsim.sensors.experimental.physics import IMU, IMUSensor  # noqa: WPS433

    fp = ns.lstrip("/") + "/"
    imu_local = np.array(imu_local)
    imu_prim_path = f"{body_path}/zed_imu_link"
    # The experimental sensor has no `frequency`: it samples every physics step, which is what the graph
    # below reads (OnPhysicsStep); `imu_rate` is only logged now.
    imu_sensor = IMUSensor(IMU.create(imu_prim_path, translations=[imu_local.tolist()]))

    keys = og.Controller.Keys
    if publish:  # sensors.publish_imu
        imu_graph_path = f"{body_path}/zed_imu_pub"
        # Driven by OnPhysicsStep in an on-demand graph, not OnTick: action graphs only evaluate on
        # rendered frames (1 in 4 physics steps with the launcher's render cadence), which capped the
        # IMU at ~62 Hz sim time (43 Hz measured at rtf 0.66) against the contract's 200 Hz. Now one
        # sample per physics step: 250 Hz sim time at the default physics_dt.
        (imu_graph, _, _, _) = og.Controller.edit(
            {"graph_path": imu_graph_path, "evaluator_name": "execution",
             "pipeline_stage": og.GraphPipelineStage.GRAPH_PIPELINE_STAGE_ONDEMAND},
            {
                keys.CREATE_NODES: [
                    ("on_tick", "isaacsim.core.nodes.OnPhysicsStep"),
                    ("sim_time", "isaacsim.core.nodes.IsaacReadSimulationTime"),
                    ("read_imu", "isaacsim.sensors.physics.IsaacReadIMU"),
                    ("pub_imu", "isaacsim.ros2.bridge.ROS2PublishImu"),
                ],
                keys.CONNECT: [
                    ("on_tick.outputs:step", "read_imu.inputs:execIn"),
                    ("read_imu.outputs:execOut", "pub_imu.inputs:execIn"),
                    ("read_imu.outputs:angVel", "pub_imu.inputs:angularVelocity"),
                    ("read_imu.outputs:linAcc", "pub_imu.inputs:linearAcceleration"),
                    ("read_imu.outputs:orientation", "pub_imu.inputs:orientation"),
                    ("sim_time.outputs:simulationTime", "pub_imu.inputs:timeStamp"),
                ],
                keys.SET_VALUES: [
                    ("pub_imu.inputs:topicName", "zed/zed_node/imu/data"),
                    ("pub_imu.inputs:nodeNamespace", ns),
                    ("pub_imu.inputs:frameId", f"{fp}zed_imu_link"),
                ],
            },
        )
        set_targets(
            prim=_stage_utils.get_current_stage().GetPrimAtPath(f"{imu_graph_path}/read_imu"),
            attribute="inputs:imuPrim",
            target_prim_paths=[imu_prim_path],
        )
        og.Controller.evaluate_sync(imu_graph)
        LOG.info("zed sdk rig: imu at %s -> %s/zed/zed_node/imu/data (every physics step; sensor %d Hz)",
                 imu_local, ns, int(imu_rate))
    return imu_sensor


class StreamImuFeeder:
    """Feed the physics IMU to the streamed ZED at the physics rate (the extension alone sends one sample per frame).

    Every physics step: read `imu_sensor` (the body IMU at the ZED's IMU, publish_imu), keep the last `window_s` of samples
    and write them to the camera node's `inputs:imuSamples` (local extension patch, docker/zed/patches-isaac-ext), which
    ingests each new one into the stream (ingest_imu) before the next frame. Samples go out in the camera body frame.
    """

    def __init__(self, imu_sensor, port: int, mount_rot: Rotation, window_s: float = 0.5):
        from isaacsim.core.simulation_manager import SimulationEvent, SimulationManager  # noqa: WPS433

        self.sensor, self.port, self.window_s = imu_sensor, port, window_s
        self.inv_mount = mount_rot.inv()
        self.mount_q = mount_rot
        self.samples = []
        self.attr = None
        self.n_written = 0
        self._cb = SimulationManager.register_callback(self.step, SimulationEvent.PHYSICS_POST_STEP)
        LOG.info("zed sdk rig: streaming the physics IMU every physics step into ZED port %d (ingest_imu)", port)

    def _find_attr(self):
        for graph in og.get_all_graphs():
            for node in graph.get_nodes():
                if node.get_type_name() == "sl.sensor.camera.OgnZEDSimCameraNode" and \
                        node.get_prim_path().endswith(f"/zed_{self.port}") and node.get_attribute_exists("inputs:imuSamples"):
                    LOG.info("zed sdk rig: IMU feed -> %s", node.get_prim_path())
                    return node.get_attribute("inputs:imuSamples")
        return None

    def step(self, _dt, _context=None):
        d = self.sensor.get_data()
        t = float(d["time"])
        if self.samples and t <= self.samples[-1][0]:
            return
        w = self.inv_mount.apply(np.asarray(d["angular_velocity"], dtype=float))
        a = self.inv_mount.apply(np.asarray(d["linear_acceleration"], dtype=float))
        qw, qx, qy, qz = (float(v) for v in d["orientation"])
        x, y, z, qw2 = (Rotation.from_quat([qx, qy, qz, qw]) * self.mount_q).as_quat()
        self.samples.append([t, *w, *a, qw2, x, y, z])
        while self.samples and self.samples[0][0] < t - self.window_s:
            self.samples.pop(0)
        if self.attr is None:
            self.attr = self._find_attr()
            if self.attr is None:
                return
        self.attr.set([v for s in self.samples for v in s])
        self.n_written += 1
