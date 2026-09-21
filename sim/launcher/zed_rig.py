"""
ZED Mini stereo/depth/IMU rig, attached to a Pegasus vehicle body.

Publishes directly under the contract topic names in docs/interface-contract.md
(zed/zed_node/...) instead of going through Pegasus's ROS2Backend graphical-sensor
path, whose topic naming (`<cam>/color/image_raw`) does not match the ZED wrapper.
Intrinsics are a placeholder pinhole model (HD720, ~90 deg HFOV) — replace with the
factory K once the real unit is measured (docs/hardware.md "ZED Mini model table").

Called from sim/launcher/launch.py after the vehicle prim exists (needs
`{vehicle.prim_path}/body`, created by Multirotor.__init__).
"""
import logging
import math

import numpy as np
import omni.graph.core as og
from isaacsim.core.utils import stage as _stage_utils
from isaacsim.core.utils.prims import set_targets
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.ros2.bridge import read_camera_info
from isaacsim.sensors.camera.camera import Camera
from isaacsim.sensors.physics import IMUSensor
from scipy.spatial.transform import Rotation
import omni.replicator.core as rep
import omni.syntheticdata as syntheticdata

LOG = logging.getLogger("launch")

# REP-103: FLU sensor frame (x-forward, y-left, z-up) -> REP-103 optical frame
# (x-right, y-down, z-forward). Standard camera-to-optical rotation.
_OPTICAL_QUAT = Rotation.from_euler("xyz", [-90.0, 0.0, -90.0], degrees=True).as_quat()  # (x,y,z,w)


def _quat_xyzw(rot: Rotation):
    q = rot.as_quat()
    return {"x": float(q[0]), "y": float(q[1]), "z": float(q[2]), "w": float(q[3])}


def attach_zed_mini(vehicle, ns: str, cfg: dict):
    """Build the ZED Mini rig on `vehicle` (a Pegasus Multirotor) and publish it
    under ROS 2 namespace `ns` (e.g. "/drone_1"), matching the interface contract.

    cfg keys (all optional, see sim/configs/*.yaml `sensors.zed`):
      mount_xyz_rpy: [x,y,z,roll_deg,pitch_deg,yaw_deg] of zed_camera_link on base_link (FLU)
      baseline: stereo baseline, metres (ZED Mini = 0.063)
      resolution: [width, height] (HD720 = [1280, 720])
      fps: camera update rate
      imu_rate: IMU publish rate (ZED Mini wrapper = 200)
      depth_range: [near, far] metres
    """
    enable_extension("isaacsim.ros2.bridge")
    enable_extension("isaacsim.sensors.physics")

    mount = [float(x) for x in cfg.get("mount_xyz_rpy", [0.10, 0.0, -0.02, 0, 0, 0])]
    mount_xyz, mount_rpy = mount[:3], mount[3:]
    baseline = float(cfg.get("baseline", 0.063))
    width, height = [int(x) for x in cfg.get("resolution", [1280, 720])]
    fps = float(cfg.get("fps", 30.0))
    imu_rate = float(cfg.get("imu_rate", 200.0))
    near, far = [float(x) for x in cfg.get("depth_range", [0.1, 15.0])]

    body_path = f"{vehicle.prim_path}/body"
    mount_rot = Rotation.from_euler("ZYX", [mount_rpy[2], mount_rpy[1], mount_rpy[0]], degrees=True)
    # interface-contract.md: "Frames (per drone, prefixed drone_<n>/ on TF)".
    fp = ns.lstrip("/") + "/"

    # ZED Mini HD720 placeholder pinhole intrinsics (TBD in docs/hardware.md until measured).
    fx = fy = (width / 2.0) / math.tan(math.radians(84.0) / 2.0)
    cx, cy = width / 2.0, height / 2.0
    diag_fov = math.degrees(2 * math.atan(math.hypot(width, height) / 2.0 / fx))

    cams = {}
    for side, y_sign in (("left", +1.0), ("right", -1.0)):
        prim_path = f"{body_path}/zed_{side}_camera_frame"
        local_pos = np.array(mount_xyz) + mount_rot.apply([0.0, y_sign * baseline / 2.0, 0.0])
        # Isaac cameras look down -Z by default; MonocularCamera's proven convention adds a
        # 180 deg yaw so "orientation 0" faces the vehicle's forward (+X, FLU).
        local_rot = mount_rot * Rotation.from_euler("Z", 180.0, degrees=True)

        cam = Camera(prim_path=prim_path, frequency=fps, resolution=(width, height))
        cam.set_local_pose(np.array(local_pos), local_rot.as_quat())
        cam.initialize()
        cam.set_lens_distortion_model("OmniLensDistortionOpenCvPinholeAPI")
        cam.set_rational_polynomial_properties(
            nominal_width=width, nominal_height=height,
            optical_centre_x=cx, optical_centre_y=cy,
            max_fov=diag_fov, distortion_model=[0.0] * 8,
        )
        cam.set_clipping_range(near, far)
        if side == "left":
            cam.add_distance_to_image_plane_to_frame()
        cams[side] = cam
        LOG.info("zed rig: %s camera at %s (prim %s)", side, local_pos, prim_path)

    for side, cam in cams.items():
        render_path = cam._render_product_path
        LOG.info("zed rig: %s render_product_path=%r", side, render_path)
        frame_id = f"{fp}zed_{side}_camera_optical_frame"

        writer_rgb = rep.writers.get("LdrColorSDROS2PublishImage")
        writer_rgb.initialize(nodeNamespace=ns, topicName=f"zed/zed_node/{side}/image_rect_color",
                               frameId=frame_id, queueSize=1)
        writer_rgb.attach([render_path])

        info, _ = read_camera_info(render_product_path=render_path)
        writer_info = rep.writers.get("ROS2PublishCameraInfo")
        writer_info.initialize(
            nodeNamespace=ns, topicName=f"zed/zed_node/{side}/camera_info", frameId=frame_id, queueSize=1,
            width=info.width, height=info.height, projectionType=info.distortion_model,
            k=info.k.reshape([1, 9]), r=info.r.reshape([1, 9]), p=info.p.reshape([1, 12]),
            physicalDistortionModel=info.distortion_model, physicalDistortionCoefficients=info.d,
        )
        writer_info.attach([render_path])

        if side == "left":
            writer_depth = rep.writers.get("DistanceToImagePlaneSDROS2PublishImage")
            writer_depth.initialize(nodeNamespace=ns, topicName="zed/zed_node/depth/depth_registered",
                                     frameId=frame_id, queueSize=1)
            writer_depth.attach([render_path])

        gate_path = syntheticdata.SyntheticData._get_node_path("PostProcessDispatchIsaacSimulationGate", render_path)
        try:
            og.Controller.attribute(gate_path + ".inputs:step").set(max(1, int(round(60.0 / fps))))
        except Exception as exc:  # noqa: BLE001 — a missed rate gate must not abort the rig build
            LOG.warning("zed rig: could not set %s publish rate gate (%s)", side, exc)

    # --- IMU: physically-simulated sensor on zed_imu_link, published at imu_rate ---
    imu_prim_path = f"{body_path}/zed_imu_link"
    imu_local = np.array(mount_xyz)
    IMUSensor(prim_path=imu_prim_path, name="zed_imu", frequency=int(imu_rate), translation=imu_local)

    imu_graph_path = f"{body_path}/zed_imu_pub"
    keys = og.Controller.Keys
    (imu_graph, _, _, _) = og.Controller.edit(
        {"graph_path": imu_graph_path, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("on_tick", "omni.graph.action.OnTick"),
                ("sim_time", "isaacsim.core.nodes.IsaacReadSimulationTime"),
                ("read_imu", "isaacsim.sensors.physics.IsaacReadIMU"),
                ("pub_imu", "isaacsim.ros2.bridge.ROS2PublishImu"),
            ],
            keys.CONNECT: [
                ("on_tick.outputs:tick", "read_imu.inputs:execIn"),
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
    LOG.info("zed rig: imu at %s -> %s/zed/zed_node/imu/data (%d Hz)", imu_local, ns, int(imu_rate))

    # --- static TF for the rig: base_link -> zed_camera_link -> {left,right} -> optical, + imu ---
    tf_graph_path = f"{body_path}/zed_tf_pub"
    optical_q = {"x": float(_OPTICAL_QUAT[0]), "y": float(_OPTICAL_QUAT[1]), "z": float(_OPTICAL_QUAT[2]), "w": float(_OPTICAL_QUAT[3])}
    frames = [
        # (child, parent, translation, quat_xyzw) — frame names carry the drone_<n>/ prefix (contract).
        (f"{fp}zed_camera_link", f"{fp}base_link", mount_xyz, _quat_xyzw(mount_rot)),
        (f"{fp}zed_left_camera_frame", f"{fp}zed_camera_link", [0.0, baseline / 2.0, 0.0], _quat_xyzw(Rotation.identity())),
        (f"{fp}zed_right_camera_frame", f"{fp}zed_camera_link", [0.0, -baseline / 2.0, 0.0], _quat_xyzw(Rotation.identity())),
        (f"{fp}zed_left_camera_optical_frame", f"{fp}zed_left_camera_frame", [0.0, 0.0, 0.0], optical_q),
        (f"{fp}zed_right_camera_optical_frame", f"{fp}zed_right_camera_frame", [0.0, 0.0, 0.0], optical_q),
        (f"{fp}zed_imu_link", f"{fp}zed_camera_link", (imu_local - np.array(mount_xyz)).tolist(), _quat_xyzw(Rotation.identity())),
    ]
    create_nodes = [
        ("on_tick", "omni.graph.action.OnTick"),
        ("sim_time", "isaacsim.core.nodes.IsaacReadSimulationTime"),
    ]
    connect = []
    set_values = []
    for i, (child, parent, t, q) in enumerate(frames):
        n = f"tf_{i}"
        create_nodes.append((n, "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"))
        connect.append(("on_tick.outputs:tick", f"{n}.inputs:execIn"))
        connect.append(("sim_time.outputs:simulationTime", f"{n}.inputs:timeStamp"))
        set_values += [
            (f"{n}.inputs:parentFrameId", parent),
            (f"{n}.inputs:childFrameId", child),
            (f"{n}.inputs:translation", [float(x) for x in t]),
            (f"{n}.inputs:rotation", [q["x"], q["y"], q["z"], q["w"]]),
            (f"{n}.inputs:staticPublisher", True),
            (f"{n}.inputs:topicName", "tf_static"),
            (f"{n}.inputs:nodeNamespace", ns),
        ]
    (tf_graph, _, _, _) = og.Controller.edit(
        {"graph_path": tf_graph_path, "evaluator_name": "execution"},
        {keys.CREATE_NODES: create_nodes, keys.CONNECT: connect, keys.SET_VALUES: set_values},
    )
    og.Controller.evaluate_sync(tf_graph)
    LOG.info("zed rig: static tf published on %s/tf_static (%d frames)", ns, len(frames))
