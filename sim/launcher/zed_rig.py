"""
ZED Mini stereo/depth/IMU rig, attached to a Pegasus vehicle body.

Publishes directly under the contract topic names in docs/interface-contract.md
(zed/zed_node/...) instead of going through Pegasus's ROS2Backend graphical-sensor
path, whose topic naming (`<cam>/color/image_raw`) does not match the ZED wrapper.
Intrinsics are a placeholder pinhole model (HD720, 84 deg HFOV) — replace with the
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


def _quat_wxyz(rot: Rotation):
    """Isaac Sim core APIs (set_local_pose, set_world_pose) take quaternions scalar-first."""
    x, y, z, w = rot.as_quat()
    return np.array([w, x, y, z])


def _quat_xyzw(rot: Rotation):
    q = rot.as_quat()
    return {"x": float(q[0]), "y": float(q[1]), "z": float(q[2]), "w": float(q[3])}


def attach_zed_mini(vehicle, ns: str, cfg: dict, features=None):
    """Build the ZED Mini rig on `vehicle` (a Pegasus Multirotor) and publish it
    under ROS 2 namespace `ns` (e.g. "/drone_1"), matching the interface contract.

    cfg keys (all optional, see sim/configs/*.yaml `sensors.zed`):
      mount_xyz_rpy: [x,y,z,roll_deg,pitch_deg,yaw_deg] of zed_camera_link on base_link (FLU)
      baseline: stereo baseline, metres (ZED Mini = 0.063)
      resolution: [width, height] (HD720 = [1280, 720])
      fps: camera update rate
      imu_rate: IMU publish rate (ZED Mini wrapper = 200)
      depth_range: [near, far] metres
      preview / preview_hz: GUI window with left image + depth (sim/launcher/zed_preview.py)
    features: zed_features.Features — the zed_wrapper switches (deploy/jetson/zed_params.yaml).
      Here: video.publish_left_right, depth.publish_depth_map, sensors.publish_imu. None = all on.

    Returns {"left": Camera, "right": Camera, "fx", "fy", "cx", "cy"} (intrinsics in pixels).
    """
    enable_extension("isaacsim.ros2.bridge")
    enable_extension("isaacsim.sensors.physics")

    mount = [float(x) for x in cfg.get("mount_xyz_rpy", [0.18, 0.0, -0.02, 0, 0, 0])]
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
    # image_rect_color is rectified, so an ideal pinhole with zero distortion is the right model.
    fx = (width / 2.0) / math.tan(math.radians(84.0) / 2.0)
    # USD pinhole: fx [px] = focalLength / horizontalAperture * width. Only the ratio matters; a 3 um
    # pixel pitch gives mm-sized numbers. Square pixels, principal point at the image centre.
    pixel_mm = 0.003
    focal_mm = fx * pixel_mm

    cams = {}
    for side, y_sign in (("left", +1.0), ("right", -1.0)):
        prim_path = f"{body_path}/zed_{side}_camera_frame"
        local_pos = np.array(mount_xyz) + mount_rot.apply([0.0, y_sign * baseline / 2.0, 0.0])
        # camera_axes="world" (the default) is +X forward / +Z up, i.e. FLU, so the mount rotation alone
        # points the lens along base_link +X. Isaac wants the quaternion scalar-first (w, x, y, z);
        # scipy's as_quat() is (x, y, z, w). Passing it unconverted (until 2026-09-25) read identity as
        # a 180 deg yaw — the rig looked backwards; a compensating "180 deg yaw" copied from Pegasus's
        # MonocularCamera (whose 180 deg roll is the same trick) turned into a 180 deg pitch.
        cam = Camera(prim_path=prim_path, frequency=fps, resolution=(width, height))
        cam.set_local_pose(np.array(local_pos), _quat_wxyz(mount_rot), camera_axes="world")
        cam.initialize()
        # Intrinsics straight on the USD camera; read_camera_info() derives camera_info K from these.
        # (A lens-distortion model with its own fx never reached the render: K stayed at the USD
        # default 50 mm focal length, ~24 deg HFOV instead of 84.)
        cam.prim.GetAttribute("focalLength").Set(focal_mm)
        cam.prim.GetAttribute("horizontalAperture").Set(width * pixel_mm)
        cam.prim.GetAttribute("verticalAperture").Set(height * pixel_mm)
        cam.set_clipping_range(near, far)
        if side == "left":
            cam.add_distance_to_image_plane_to_frame()
        cams[side] = cam
        LOG.info("zed rig: %s camera at %s (prim %s), fx=%.1f px (HFOV 84 deg)", side, local_pos, prim_path, fx)

    def on(key):
        return True if features is None else features.on(key, True)
    pub_images, pub_depth, pub_imu = on("video.publish_left_right"), on("depth.publish_depth_map"), on("sensors.publish_imu")

    for side, cam in cams.items():
        render_path = cam._render_product_path
        LOG.info("zed rig: %s render_product_path=%r", side, render_path)
        frame_id = f"{fp}zed_{side}_camera_optical_frame"

        if pub_images:  # video.publish_left_right
            writer_rgb = rep.writers.get("LdrColorSDROS2PublishImage")
            writer_rgb.initialize(nodeNamespace=ns, topicName=f"zed/zed_node/{side}/image_rect_color",
                                   frameId=frame_id, queueSize=1)
            writer_rgb.attach([render_path])

        info, _ = read_camera_info(render_product_path=render_path)
        # Stereo consumers (stereo_image_proc, Isaac ROS disparity, cuVSLAM) read the baseline from the RIGHT camera's
        # projection matrix: P[0,3] = -fx * baseline, exactly what the ZED wrapper publishes. read_camera_info() leaves
        # it 0, which makes every stereo node see a zero baseline (depth = inf / meaningless). docs/perception.md.
        p_mat = np.array(info.p, dtype=np.float64).reshape(3, 4)
        if side == "right":
            p_mat[0, 3] = -float(info.k[0]) * baseline
        info.p = p_mat.reshape(-1)
        writer_info = rep.writers.get("ROS2PublishCameraInfo")
        writer_info.initialize(
            nodeNamespace=ns, topicName=f"zed/zed_node/{side}/camera_info", frameId=frame_id, queueSize=1,
            width=info.width, height=info.height, projectionType=info.distortion_model,
            k=info.k.reshape([1, 9]), r=info.r.reshape([1, 9]), p=info.p.reshape([1, 12]),
            physicalDistortionModel=info.distortion_model, physicalDistortionCoefficients=info.d,
        )
        writer_info.attach([render_path])

        if side == "left" and pub_depth:  # depth.publish_depth_map
            writer_depth = rep.writers.get("DistanceToImagePlaneSDROS2PublishImage")
            writer_depth.initialize(nodeNamespace=ns, topicName="zed/zed_node/depth/depth_registered",
                                     frameId=frame_id, queueSize=1)
            writer_depth.attach([render_path])

        # Publish every `gate_step`-th rendered frame (the launcher renders ~60 Hz sim). camera_info uses the
        # PostProcessDispatch gate; each image writer has its OWN per-render-var gate (<rendervar>IsaacSimulationGate)
        # which was never set, so images went out at the full render rate, twice camera_info (bugs.md B9). Stereo /
        # VSLAM consumers need image + camera_info to pair 1:1, so all gates now get the same step.
        gate_step = max(1, int(round(60.0 / fps)))
        gates = ["PostProcessDispatchIsaacSimulationGate"]
        if pub_images:
            gates.append(f"{syntheticdata.SyntheticData.convert_sensor_type_to_rendervar('LdrColor')}IsaacSimulationGate")
        if side == "left" and pub_depth:
            gates.append(f"{syntheticdata.SyntheticData.convert_sensor_type_to_rendervar('DistanceToImagePlane')}IsaacSimulationGate")
        for gate in gates:
            try:
                og.Controller.attribute(syntheticdata.SyntheticData._get_node_path(gate, render_path) + ".inputs:step").set(gate_step)
            except Exception as exc:  # noqa: BLE001 — a missed rate gate must not abort the rig build
                LOG.warning("zed rig: could not set %s %s rate gate (%s)", side, gate, exc)

    # --- IMU: physically-simulated sensor on zed_imu_link, published at imu_rate ---
    imu_prim_path = f"{body_path}/zed_imu_link"
    imu_local = np.array(mount_xyz)
    IMUSensor(prim_path=imu_prim_path, name="zed_imu", frequency=int(imu_rate), translation=imu_local)

    keys = og.Controller.Keys
    if pub_imu:  # sensors.publish_imu
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
        LOG.info("zed rig: imu at %s -> %s/zed/zed_node/imu/data (every physics step; sensor %d Hz)",
                 imu_local, ns, int(imu_rate))

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
    # Pinhole intrinsics of both cameras (square pixels, principal point at the centre).
    LOG.info("zed rig: publishing left/right images %s, depth map %s, imu %s (zed_wrapper switches)",
             pub_images, pub_depth, pub_imu)
    return {**cams, "fx": fx, "fy": fx, "cx": width / 2.0, "cy": height / 2.0, "baseline": baseline}
