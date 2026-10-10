"""zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim (docker/compose.yaml `zed`) and the
real drone (docker/compose.yaml `drone-zed`), so the two cannot drift.

    ros2 launch /workspace/docker/zed/zed_drone.launch.py drone_id:=1 params:=<compiled params.yaml> [sim_mode:=true sim_port:=30000]

Why not just `zed_camera.launch.py namespace:=drone_1`: the stock launch then names the node after the camera and
publishes under `/drone_1/zed/...`, without the `zed_node` segment. docs/interface-contract.md fixes
`/drone_<n>/zed/zed_node/...`, which is what you get with the DEFAULT launch (`/zed/zed_node/...`) when the whole
thing is pushed into the `drone_<n>` namespace — exactly what this file does.

One catch: the stock launch loads its node into a container named `/zed/zed_container` (absolute, built without the
pushed namespace), while the container itself now lives at `/drone_<n>/zed/zed_container`, so the load call would wait
forever. The remap below points the container's load service at the name the launch is looking for. The loaded node
still lands in `/drone_<n>/zed/`.

Second catch: the stock launch also sets `pos_tracking.publish_tf`, `pos_tracking.publish_map_tf` and `sensors.publish_imu_tf`
from its own launch arguments (default true), AFTER the params file, so zed.yaml's values never reached the node (ros-graph.md
R2). They are read from the params file and forwarded as those launch arguments.

Drone TF (interface-contract.md, R3): the wrapper's base frame is hard-wired to `zed_camera_link`, so it publishes
odom -> zed_camera_link and nothing can sit between. This file adds the two links that join it to the vehicle:
  zed_camera_link -> base_link   static, the inverse of the camera mount = `pos_tracking.initial_base_pose` in zed.yaml (the
                                 camera pose at the start of tracking, so `odom` starts at base_link's start pose)
  map -> odom                    static identity (the wrapper's own map TF is off, `publish_map_tf: false`)
so odom -> base_link and base_link -> zed_camera_link both resolve. Only while the wrapper publishes its TF (`publish_tf`).

Any process that dies with an error ends the whole launch (R9): without this the wrapper's component container could abort
while `ros2 launch` and the docker container stayed up, so `restart:` never fired and `docker ps` looked healthy. The launch
then exits 0: the drone's `restart: unless-stopped` restarts the camera; the sim's `restart: on-failure` leaves it down, which
is right there (the SDK connects once per sim run, B18).
"""
import math

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, GroupAction, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.substitutions import FindPackageShare

TF_ARGS = {"publish_tf": ("pos_tracking", "publish_tf"), "publish_map_tf": ("pos_tracking", "publish_map_tf"),
           "publish_imu_tf": ("sensors", "publish_imu_tf")}
CAMERA_LINK = "zed_camera_link"          # the wrapper's <camera_name>_camera_link (camera_name zed)


def params(params_path):
    """The ros__parameters of the compiled params file ({} without one)."""
    if not params_path:
        return {}
    with open(params_path) as f:
        return ((yaml.safe_load(f) or {}).get("/**") or {}).get("ros__parameters") or {}


def tf_args(p):
    """{launch arg: "true"|"false"} for the TF switches the params set; absent ones keep the stock default."""
    return {arg: str(p[sec][key]).lower() for arg, (sec, key) in TF_ARGS.items() if key in (p.get(sec) or {})}


def inverse_pose(x, y, z, roll, pitch, yaw):
    """(t, q) of the inverse of the pose x y z + intrinsic ZYX roll pitch yaw: t = -R^T p, q = conj(q_rpy) as (x, y, z, w)."""
    cr, sr, cp, sp, cy, sy = (f(a / 2) for a in (roll, pitch, yaw) for f in (math.cos, math.sin))
    q = (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)
    qx, qy, qz, qw = q
    r = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
         [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
         [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
    t = [-sum(r[i][j] * v for i, v in enumerate((x, y, z))) for j in range(3)]
    return t, (-qx, -qy, -qz, qw)


def static_tf(name, parent, child, t=(0.0, 0.0, 0.0), q=(0.0, 0.0, 0.0, 1.0)):
    args = []
    for k, v in zip(("--x", "--y", "--z", "--qx", "--qy", "--qz", "--qw"), (*t, *q)):
        args += [k, repr(float(v))]
    return Node(package="tf2_ros", executable="static_transform_publisher", name=name, output="log",
                arguments=args + ["--frame-id", parent, "--child-frame-id", child])


def drone_tf(p):
    pt = p.get("pos_tracking") or {}
    if not pt.get("publish_tf", True):
        return []
    mount = [float(v) for v in (pt.get("initial_base_pose") or [0.0] * 6)]
    nodes = [static_tf("tf_camera_base", CAMERA_LINK, "base_link", *inverse_pose(*mount))]
    if not pt.get("publish_map_tf", True):
        nodes.append(static_tf("tf_map_odom", pt.get("map_frame", "map"), pt.get("odometry_frame", "odom")))
    return nodes


def _zed(context):
    p = params(LaunchConfiguration("params").perform(context))
    return drone_tf(p) + [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare("zed_wrapper"), "launch", "zed_camera.launch.py"])),
        launch_arguments={
            "camera_model": LaunchConfiguration("camera_model"),
            "ros_params_override_path": LaunchConfiguration("params"),
            "sim_mode": LaunchConfiguration("sim_mode"),
            "sim_address": LaunchConfiguration("sim_address"),
            "sim_port": LaunchConfiguration("sim_port"),
            **tf_args(p),
        }.items(),
    )]


def generate_launch_description():
    declared = [
        DeclareLaunchArgument("drone_id", default_value="1", description="1-based drone number -> namespace drone_<n>"),
        DeclareLaunchArgument("camera_model", default_value="zedm"),
        DeclareLaunchArgument("params", default_value="", description="params override YAML (the file `python3 -m zed_stack compile` writes from docker/zed/zed.yaml)"),
        DeclareLaunchArgument("sim_mode", default_value="false", description="true = read the Isaac Sim stream"),
        DeclareLaunchArgument("sim_address", default_value="127.0.0.1"),
        DeclareLaunchArgument("sim_port", default_value="30000"),
    ]
    ns = ["drone_", LaunchConfiguration("drone_id")]
    load_service = "/zed/zed_container/_container/load_node"
    return LaunchDescription(declared + [
        RegisterEventHandler(OnProcessExit(on_exit=_shutdown_on_error)),
        GroupAction([
            PushRosNamespace(ns),
            SetRemap(src=["/drone_", LaunchConfiguration("drone_id"), load_service], dst=load_service),
            OpaqueFunction(function=_zed),
        ]),
    ])


def _shutdown_on_error(event, _context):
    if event.returncode == 0:
        return None
    return [EmitEvent(event=Shutdown(reason=f"{event.action.name} exited with {event.returncode}: stopping the ZED launch"))]
