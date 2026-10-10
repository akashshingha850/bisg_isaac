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
"""
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace, SetRemap
from launch_ros.substitutions import FindPackageShare

TF_ARGS = {"publish_tf": ("pos_tracking", "publish_tf"), "publish_map_tf": ("pos_tracking", "publish_map_tf"),
           "publish_imu_tf": ("sensors", "publish_imu_tf")}


def tf_args(params_path):
    """{launch arg: "true"|"false"} for the TF switches the params file sets; absent ones keep the stock default."""
    if not params_path:
        return {}
    with open(params_path) as f:
        p = ((yaml.safe_load(f) or {}).get("/**") or {}).get("ros__parameters") or {}
    return {arg: str(p[sec][key]).lower() for arg, (sec, key) in TF_ARGS.items() if key in (p.get(sec) or {})}


def _zed(context):
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare("zed_wrapper"), "launch", "zed_camera.launch.py"])),
        launch_arguments={
            "camera_model": LaunchConfiguration("camera_model"),
            "ros_params_override_path": LaunchConfiguration("params"),
            "sim_mode": LaunchConfiguration("sim_mode"),
            "sim_address": LaunchConfiguration("sim_address"),
            "sim_port": LaunchConfiguration("sim_port"),
            **tf_args(LaunchConfiguration("params").perform(context)),
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
    return LaunchDescription(declared + [GroupAction([
        PushRosNamespace(ns),
        SetRemap(src=["/drone_", LaunchConfiguration("drone_id"), load_service], dst=load_service),
        OpaqueFunction(function=_zed),
    ])])
